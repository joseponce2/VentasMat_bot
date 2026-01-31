import os
import gspread
import logging
import json
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configuración de Logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
# ASEGÚRATE de tener la variable de entorno TELEGRAM_TOKEN en Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")

# 2. Configuración de Google Sheets (Asumimos que el secret file y APIs están OK)
sheet = None
try:
    with open('google_creds.json') as f:
        creds_json = json.load(f)
    # Importamos aquí ServiceAccountCredentials para evitar errores de importación circular previos
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ["https://spreadsheets.google.com", "https://www.googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Ventas_Bot_Datos").get_worksheet(0)
    logger.info("Conexión exitosa a Google Sheets")
except Exception as e:
    logger.error(f"Error conectando a Google Sheets: {e}")

# 3. Funciones del Bot (Ahora deben ser async)
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
        
        # Unimos los argumentos en una sola lista para append_row
        datos = list(context.args)
        
        # Insertar en la siguiente fila vacía de Google Sheets
        sheet.append_row(datos)
        await update.message.reply_text(f"✅ Registrado: {datos[0]} a ${datos[1]}")
    except Exception as e:
        logger.error(f"Error al registrar: {e}")
        await update.message.reply_text(f"❌ Error al registrar: {e}")

# 4. Configuración de Webhooks con Application
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
    # Configurar el webhook al iniciar la app
    # Render asigna dinámicamente el dominio, pero usamos la URL principal
    WEBHOOK_URL = f"https://ventasmat-bot-1.onrender.com{TELEGRAM_TOKEN}"
    # Configuramos el webhook usando asyncio para compatibilidad con PTB v22+
    asyncio.run(bot.set_webhook(WEBHOOK_URL))
    logger.info(f"Webhook configurado en: {WEBHOOK_URL}")

    # Iniciar Flask (Render usará esta parte para mantener el servicio vivo)
    port = int(os.environ.get("PORT", 10000))
    # Usamos '0.0.0.0' para que sea accesible externamente en Render
    app.run(host='0.0.0.0', port=port, debug=False)
