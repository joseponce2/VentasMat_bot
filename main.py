import os
import gspread
import logging
import json
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")
    # Si no hay token, la app no puede iniciar correctamente
    exit(1) 

# 2. Configuración de Google Sheets (Usando método moderno)
sheet = None
try:
    with open('google_creds.json', 'r') as f:
        creds_json = json.load(f)
    
    # Nuevo método: usar from_service_account_info directamente con el diccionario
    client = gspread.service_account_from_dict(creds_json)
    
    sheet = client.open("Ventas_Bot_Datos").get_worksheet(0)
    logger.info("Conexión exitosa a Google Sheets")
except Exception as e:
    logger.error(f"Error conectando a Google Sheets: {e}")
    # Si Sheets falla, el bot aún puede iniciar, pero las funciones fallarán.

# 3. Funciones del Bot (Async)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("¡Hola! Soy tu bot de ventas. Usa /registrar para anotar una venta.")

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if sheet is None:
        await update.message.reply_text("❌ Error: El bot no pudo conectar con Google Sheets. Revisa los logs de Render y los permisos de la API.")
        return

    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Uso: /registrar [Producto] [Precio]")
            return
        
        datos = list(context.args)
        
        sheet.append_row(datos)
        await update.message.reply_text(f"✅ Registrado: {context.args} en la hoja.")
    except Exception as e:
        logger.error(f"Error al registrar: {e}")
        await update.message.reply_text(f"❌ Error al registrar: {e}")

# 4. Configuración de Webhooks y la aplicación
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("registrar", registrar))

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
async def process_update():
    """Endpoint para que Render reciba las actualizaciones de Telegram."""
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    return "ok"

@app.route('/')
def health_check():
    """Endpoint de salud para Render."""
    return "Bot is running", 200

# 5. Ejecución Principal
if __name__ == '__main__':
    # Usamos application.run_webhook para manejar todo el setup de Render correctamente
    # Render espera que el puerto 10000 responda HTTP.
    port = int(os.environ.get("PORT", 10000))
    WEBHOOK_URL = f"https://ventasmat-bot-1.onrender.com"
    
    # Inicia el servidor Flask y configura el webhook en Telegram
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=f"/{TELEGRAM_TOKEN}",
        webhook_url=WEBHOOK_URL + TELEGRAM_TOKEN
    )
