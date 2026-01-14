import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

# Cargar llaves
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN)

# --- COMANDO /START ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Enlace directo a tu imagen de portada en GitHub
    img_url = "https://raw.githubusercontent.com/TheGoblinGame420/el-duende-hub/main/webapp/static/imagen_portada_home.png"
    
    caption = (
        "🔥 *$ELDUENDE ESTÁ ONLINE*\n\n"
        "Bienvenido al ecosistema desarrollado por @elduendepnp en la red de *Solana*.\n\n"
        "🎮 *GameFi:* Juega y gana tokens reales.\n"
        "🛡 *Seguridad:* Infraestructura auditada.\n"
        "🚀 *Misión:* Crear el movimiento más fuerte de Latam.\n\n"
        "👇 *¡INICIA EL SISTEMA AHORA!*"
    )
    
    markup = InlineKeyboardMarkup()
    
    # Botón 1: Jugar
    btn_play = InlineKeyboardButton(
        text="🚀 JUGAR AHORA", 
        web_app=WebAppInfo(url="https://el-duende-app.onrender.com")
    )
    
    # Botón 2: Comunidad
    btn_channel = InlineKeyboardButton(text="📢 Comunidad Oficial", url="https://t.me/elduende420peru")
    
    markup.add(btn_play)
    markup.add(btn_channel)

    try:
        bot.send_photo(message.chat.id, img_url, caption=caption, parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        print(f"Error enviando foto: {e}")
        # Fallback por si la imagen tarda en cargar
        bot.send_message(message.chat.id, caption, parse_mode='Markdown', reply_markup=markup)

print("Bot Iniciado...")
bot.infinity_polling()
