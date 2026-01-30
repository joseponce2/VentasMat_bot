import os
import gspread
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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
try:
    # Usamos el archivo que creamos en el paso anterior en Render
    client = gspread.service_account(filename='google_creds.json')
    sheet = client.open("Ventas_Bot_Datos").get_worksheet(0)
    print("Conexión exitosa a Google Sheets")
except Exception as e:
    print(f"Error conectando a Google Sheets: {e}")

# 3. Funciones del Bot de Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de ventas. Usa /registrar para anotar una venta.")

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ejemplo simple de registro: /registrar Producto Precio
    try:
        datos = context.args
        if len(datos) < 2:
            await update.message.reply_text("Uso: /registrar [Producto] [Precio]")
            return
        
        producto = datos[0]
        precio = datos[1]
        
        # Insertar en la siguiente fila vacía de Google Sheets
        sheet.append_row([producto, precio])
        await update.message.reply_text(f"✅ Registrado: {producto} a ${precio}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al registrar: {e}")

# 4. Ejecución Principal
if __name__ == '__main__':
    # Configurar Logs
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # Iniciar Flask en un hilo separado
    Thread(target=run_flask).start()

    # Configurar Bot de Telegram
    # ASEGÚRATE de tener la variable de entorno TELEGRAM_TOKEN en Render
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("ERROR: No se encontró la variable de entorno TELEGRAM_TOKEN")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Comandos
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('registrar', registrar))
        
        print("Bot iniciado...")
        application.run_polling()
