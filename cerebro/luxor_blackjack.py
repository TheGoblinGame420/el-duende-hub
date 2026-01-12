import logging
import secrets
import os
import sys
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CARGAR SECRETOS ESPECÍFICOS DEL CASINO ---
load_dotenv()
# Aquí le decimos que use la llave del CASINO, no la del Trader
TOKEN = os.getenv("CASINO_TOKEN") 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- RECURSOS VISUALES ---
PALOS = ['♠️', '♥️', '♦️', '♣️']
VALORES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def obtener_carta_segura():
    return secrets.choice(VALORES), secrets.choice(PALOS)

def calcular_puntaje(mano):
    total = 0
    ases = 0
    for valor, palo in mano:
        if valor in ['J', 'Q', 'K']: total += 10
        elif valor == 'A': 
            ases += 1
            total += 11
        else: total += int(valor)
    while total > 21 and ases > 0:
        total -= 10
        ases -= 1
    return total

def mostrar_mano(mano, ocultar_primera=False):
    if ocultar_primera:
        return f"🎴 [Oculta]  " + "  ".join([f"{v}{p}" for v, p in mano[1:]])
    return "  ".join([f"{v}{p}" for v, p in mano])

# --- LÓGICA DEL JUEGO ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Damos saldo de bienvenida si es nuevo
    if 'saldo' not in context.user_data: 
        context.user_data['saldo'] = 500
        
    teclado = [[InlineKeyboardButton("🃏 Jugar BlackJack (50 LXR)", callback_data='new_game')]]
    
    await update.message.reply_text(
        f"🎰 **LUXOR CASINO** 🎰\n\n"
        f"👤 Jugador: {update.effective_user.first_name}\n"
        f"💰 Saldo: {context.user_data['saldo']} LXR\n"
        f"📝 Reglas: El Dealer se planta en 17.",
        reply_markup=InlineKeyboardMarkup(teclado), 
        parse_mode="Markdown"
    )

async def nuevo_juego(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Verificar saldo
    if context.user_data.get('saldo', 0) < 50:
        await query.edit_message_text("🚫 **SALDO INSUFICIENTE**\n\nPide una recarga al Admin.")
        return

    # Cobrar entrada
    context.user_data['saldo'] -= 50
    
    # Repartir
    context.user_data['mano_jugador'] = [obtener_carta_segura(), obtener_carta_segura()]
    context.user_data['mano_dealer'] = [obtener_carta_segura(), obtener_carta_segura()]
    context.user_data['juego_activo'] = True
    
    # Verificar BlackJack instantáneo (21 a la primera)
    if calcular_puntaje(context.user_data['mano_jugador']) == 21:
        await finalizar_juego(query, context, "🚀 ¡BLACKJACK NATURAL! (x2.5)", 125)
    else:
        await actualizar_tablero(query, context)

async def acciones_juego(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    accion = query.data
    
    if not context.user_data.get('juego_activo'): return

    if accion == 'hit':
        context.user_data['mano_jugador'].append(obtener_carta_segura())
        if calcular_puntaje(context.user_data['mano_jugador']) > 21:
            await finalizar_juego(query, context, "💥 TE PASASTE (Bust)", 0)
        else:
            await actualizar_tablero(query, context)
            
    elif accion == 'stand':
        dealer = context.user_data['mano_dealer']
        while calcular_puntaje(dealer) < 17:
            dealer.append(obtener_carta_segura())
        
        p_dealer = calcular_puntaje(dealer)
        p_jugador = calcular_puntaje(context.user_data['mano_jugador'])
        
        ganancia = 0
        resultado = ""
        
        if p_dealer > 21: 
            resultado = "🏆 DEALER SE PASÓ. ¡GANASTE!"
            ganancia = 100
        elif p_dealer > p_jugador: 
            resultado = "💀 LA CASA GANA."
            ganancia = 0
        elif p_dealer < p_jugador: 
            resultado = "🎉 ¡GANASTE!"
            ganancia = 100
        else: 
            resultado = "🤝 EMPATE (Te devuelvo tus 50)"
            ganancia = 50
            
        await finalizar_juego(query, context, resultado, ganancia)

async def actualizar_tablero(query, context):
    dealer = mostrar_mano(context.user_data['mano_dealer'], ocultar_primera=True)
    jugador = mostrar_mano(context.user_data['mano_jugador'])
    puntos = calcular_puntaje(context.user_data['mano_jugador'])
    
    msg = (
        f"🎰 **MESA DE JUEGO** 🎰\n\n"
        f"👨‍💼 **Dealer:** {dealer}\n"
        f"👤 **Tú ({puntos}):** {jugador}"
    )
    teclado = [[InlineKeyboardButton("🟢 Pedir Carta", callback_data='hit'), InlineKeyboardButton("🔴 Plantarse", callback_data='stand')]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(teclado), parse_mode="Markdown")

async def finalizar_juego(query, context, resultado, ganancia):
    context.user_data['juego_activo'] = False
    context.user_data['saldo'] += ganancia
    dealer = mostrar_mano(context.user_data['mano_dealer'])
    jugador = mostrar_mano(context.user_data['mano_jugador'])
    p_dealer = calcular_puntaje(context.user_data['mano_dealer'])
    p_jugador = calcular_puntaje(context.user_data['mano_jugador'])
    
    msg = (
        f"**{resultado}**\n\n"
        f"👨‍💼 **Dealer ({p_dealer}):** {dealer}\n"
        f"👤 **Tú ({p_jugador}):** {jugador}\n\n"
        f"💰 Saldo Actual: {context.user_data['saldo']} LXR"
    )
    teclado = [[InlineKeyboardButton("🔄 Jugar Otra Vez", callback_data='new_game')]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(teclado), parse_mode="Markdown")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ ERROR: No se encontró 'CASINO_TOKEN' en el archivo .env")
        sys.exit()
        
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(nuevo_juego, pattern='new_game'))
    app.add_handler(CallbackQueryHandler(acciones_juego, pattern='hit|stand'))
    
    print("--- 🎰 LUXOR CASINO DEALER LISTO ---")
    app.run_polling()