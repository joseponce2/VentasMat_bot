import os
import gspread
import logging
import json
from flask import Flask, request, jsonify
from threading import Thread
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
# ASEGÚRATE de tener la variable de entorno TELEGRAM_TOKEN en Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)

# 2. Configuración de Google Sheets
sheet = None
try:
    with open('google_creds.json') as f:
        creds_json = json.load(f)
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ["https://spreadsheets.google.com", "https://www.googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Ventas_Bot_Datos").get_worksheet(0)
    logger.info("Conexión exitosa a Google Sheets")
except Exception as e:
    logger.error(f"Error conectando a Google Sheets: {e}")

# 3. Funciones del Bot de Telegram
def start(update: Update, context):
    update.message.reply_text("¡Hola! Soy tu bot de ventas. Usa /registrar para anotar una venta.")

def registrar(update: Update, context):
    if sheet is None:
        update.message.reply_text("❌ Error: El bot no pudo conectar con Google Sheets. Revisa los logs de Render y los permisos de la API.")
        return

    try:
        if not context.args or len(context.args) < 2:
            update.message.reply_text("Uso: /registrar [Producto] [Precio]")
            return
        
        producto = context.args[0]
        precio = context.args[1]
        
        sheet.append_row([producto, precio])
        update.message.reply_text(f"✅ Registrado: {producto} a ${precio}")
    except Exception as e:
        update.message.reply_text(f"❌ Error al registrar: {e}")

# 4. Configuración de Webhooks (Soluciona el error Conflict 409)
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('registrar', registrar))

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    return "ok"

# 5. Ejecución Principal
if __name__ == '__main__':
    # Configurar el webhook al iniciar la app
    WEBHOOK_URL = f"https://ventasmat-bot-1.onrender.com{TELEGRAM_TOKEN}"
    bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook configurado en: {WEBHOOK_URL}")
    
    # Iniciar Flask (Render usará esta parte para mantener el servicio vivo)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

