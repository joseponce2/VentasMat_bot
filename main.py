import os
import gspread
import logging
import json
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from oauth2client.service_account import ServiceAccountCredentials

# 1. Configuración de Flask para Render (Evita que el servicio se detenga)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running", 200

def run_flask():
    # Render asigna un puerto dinámico en la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# 2. Configuración de Google Sheets
sheet = None # Inicializamos la variable globalmente
try:
    # Leer el archivo secreto de Render de forma explícita
    with open('google_creds.json') as f:
        creds_json = json.load(f)
    
    # Autorizar al cliente con las credenciales cargadas
    scope = ["https://spreadsheets.google.com", "https://www.googleapis.com"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    
    # Abre la hoja
    sheet = client.open("Ventas_Bot_Datos").get_worksheet(0)
    print("Conexión exitosa a Google Sheets")

except Exception as e:
    print(f"Error conectando a Google Sheets: {e}")

# 3. Funciones del Bot de Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de ventas. Usa /registrar para anotar una venta.")

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if sheet is None:
        await update.message.reply_text("❌ Error: El bot no pudo conectar con Google Sheets. Revisa los logs de Render y los permisos de la API.")
        return

    # Ejemplo simple de registro: /registrar Producto Precio
    try:
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("Uso: /registrar [Producto] [Precio]")
            return
        
        producto = context.args[0]
        precio = context.args[1]
        
        # Insertar en la siguiente fila vacía de Google Sheets
        sheet.append_row([producto, precio])
        await update.message.reply_text(f"✅ Registrado: {producto} a ${precio}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar: {e}")

# 4. Ejecución Principal
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    Thread(target=run_flask).start()

    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('registrar', registrar))
        
        print("Bot iniciado...")
        application.run_polling()
