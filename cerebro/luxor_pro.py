import ccxt
import pandas as pd
import requests
import time
import json
import os
import io
import sys
from datetime import datetime
from dotenv import load_dotenv  # Carga la seguridad
import mplfinance as mpf       # Generador de gráficos

# --- CARGAR SECRETOS DEL BÚNKER ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- CONFIGURACIÓN ---
ARCHIVO_CARTERA = "cartera_luxor.json"
INVERSION_FIJA = 10.0
ACTIVOS = {
    'BTC/USDT': {'tf': '1m', 'color': '🟠', 'tp': 0.004, 'sl': 0.002},
    'ETH/USDT': {'tf': '1m', 'color': '💠', 'tp': 0.005, 'sl': 0.003},
    'SOL/USDT': {'tf': '1m', 'color': '🟣', 'tp': 0.006, 'sl': 0.004},
    'AXS/USDT': {'tf': '1m', 'color': '🔵', 'tp': 0.008, 'sl': 0.005},
}

# --- GENERADOR DE GRÁFICOS (RAM) ---
def generar_imagen_con_niveles(df, symbol, entry, tp, sl):
    try:
        # Preparamos datos para el gráfico
        df_chart = df.copy()
        df_chart['time'] = pd.to_datetime(df_chart['time'], unit='ms')
        df_chart.set_index('time', inplace=True)

        # Estilo visual oscuro profesional
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', inherit=True)
        s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

        # Líneas de TP (Verde), Entrada (Azul), SL (Rojo)
        niveles = dict(hlines=[entry, tp, sl], 
                       colors=['#00f7ff', '#00ff00', '#ff0000'], 
                       linewidths=[1, 1.5, 1.5], linestyle='-.')

        buf = io.BytesIO()
        mpf.plot(df_chart, type='candle', style=s, volume=True, 
                 mav=(50, 100), hlines=niveles,
                 title=f"\nLUXOR SIGNAL: {symbol}",
                 savefig=dict(fname=buf, dpi=100, bbox_inches='tight'))
        buf.seek(0)
        return buf
    except Exception as e:
        print(f"⚠️ Error generando gráfico (¿Falta mplfinance?): {e}")
        return None

# --- MATEMÁTICA PURA (INDICADORES) ---
def calcular_indicadores(df):
    df['sma'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['bb_lower'] = df['sma'] - (2 * df['std'])
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    rs = gain.ewm(span=7, adjust=False).mean() / loss.ewm(span=7, adjust=False).mean()
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

# --- GESTIÓN DE CARTERA Y TELEGRAM ---
def cargar_cartera():
    if not os.path.exists(ARCHIVO_CARTERA):
        guardar_cartera({"saldo_disponible": 100.0, "valor_en_juego": 0.0, "posiciones": {}})
    with open(ARCHIVO_CARTERA, 'r') as f: return json.load(f)

def guardar_cartera(datos):
    with open(ARCHIVO_CARTERA, 'w') as f: json.dump(datos, f, indent=4)

def enviar_telegram(mensaje, imagen_buffer=None):
    try:
        if imagen_buffer:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            files = {'photo': ('chart.png', imagen_buffer)}
            data = {"chat_id": CHANNEL_ID, "caption": mensaje, "parse_mode": "Markdown"}
            requests.post(url, data=data, files=files)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": mensaje, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")

# --- CEREBRO PRINCIPAL ---
def analizar_mercado():
    cartera = cargar_cartera()
    exchange = ccxt.binance()
    hora = datetime.now().strftime('%H:%M:%S')
    
    equity = cartera['saldo_disponible'] + cartera['valor_en_juego']
    print(f"[{hora}] 👁️ LUXOR PRO | Capital: ${equity:.2f}")

    for symbol, config in ACTIVOS.items():
        try:
            # 1. GESTIÓN DE SALIDAS
            if symbol in cartera['posiciones']:
                pos = cartera['posiciones'][symbol]
                ticker = exchange.fetch_ticker(symbol)
                precio = ticker['last']
                
                accion, motivo = "HOLD", ""
                if precio >= pos['tp']: accion, motivo = "WIN", "✅ TP (Cobrar)"
                elif precio <= pos['sl']: accion, motivo = "LOSS", "🛡️ SL (Proteger)"
                
                if accion != "HOLD":
                    retorno = pos['cantidad'] * precio
                    pnl = retorno - pos['inversion_inicial']
                    cartera['saldo_disponible'] += retorno
                    cartera['valor_en_juego'] -= pos['inversion_inicial']
                    del cartera['posiciones'][symbol]
                    guardar_cartera(cartera)
                    
                    msj = (
                        f"{'🤑' if pnl>0 else '👮'} **CIERRE OPERACIÓN**\n"
                        f"🪙 **{symbol.replace('/','')}**\n"
                        f"📊 **Acción:** {motivo}\n"
                        f"⚡ **P&L:** `${pnl:.3f}`\n"
                        f"🏦 **CAPITAL:** `${(cartera['saldo_disponible'] + cartera['valor_en_juego']):.2f}`"
                    )
                    enviar_telegram(msj, None)
                continue

            # 2. BÚSQUEDA DE ENTRADAS
            if cartera['saldo_disponible'] >= INVERSION_FIJA:
                bars = exchange.fetch_ohlcv(symbol, timeframe=config['tf'], limit=80)
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df = calcular_indicadores(df)

                precio = df['close'].iloc[-1]
                bb_lower = df['bb_lower'].iloc[-1]
                rsi = df['rsi'].iloc[-1]

                # SEÑAL: Precio rompe Banda Bollinger y RSI bajo
                if (precio <= bb_lower) and (rsi < 40):
                    tp_price = precio * (1 + config['tp'])
                    sl_price = precio * (1 - config['sl'])
                    
                    # Generar IMAGEN
                    imagen_ram = generar_imagen_con_niveles(df, symbol, precio, tp_price, sl_price)
                    
                    # Ejecutar Orden Virtual
                    cantidad = INVERSION_FIJA / precio
                    cartera['posiciones'][symbol] = {
                        "precio_entrada": precio, "cantidad": cantidad,
                        "inversion_inicial": INVERSION_FIJA, "tp": tp_price, "sl": sl_price
                    }
                    cartera['saldo_disponible'] -= INVERSION_FIJA
                    cartera['valor_en_juego'] += INVERSION_FIJA
                    guardar_cartera(cartera)
                    
                    msj = (
                        f"{config['color']} **SEÑAL VISUAL DETECTADA**\n"
                        f"🦁 **{symbol.replace('/','')}**\n"
                        f"🔵 **Entrada:** `${precio}`\n"
                        f"🟢 **Meta:** `${tp_price:.4f}`\n"
                        f"🔴 **Stop:** `${sl_price:.4f}`\n"
                        f"📉 **Saldo Libre:** `${cartera['saldo_disponible']:.2f}`"
                    )
                    
                    if imagen_ram:
                        enviar_telegram(msj, imagen_ram)
                        print(f"📸 ¡Gráfico enviado para {symbol}!")
                    else:
                        enviar_telegram(msj, None)
                        print(f"⚠️ Alerta enviada SIN gráfico (Error librería).")

        except Exception as e:
            print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        print("❌ ERROR: No se encontró el archivo .env o el Token.")
        sys.exit()
    print("--- 🦁 LUXOR PRO SECURE (v10.1) ---")
    while True:
        analizar_mercado()
        time.sleep(5)