import os
from flask import Flask, request
from telegram import Bot, Update
import logging

# --- ENVIRONMENT CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
APP_URL = os.environ.get("APP_URL")  # เช่น https://your-app-name.onrender.com
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

# --- SETUP BOT AND APP ---
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- WEBHOOK ROUTE ---
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        message = update.message.text
        chat_id = update.message.chat_id

        if message == "/start":
            bot.send_message(chat_id=chat_id, text="🎉 สวัสดีครับ! บอท TKC Assistant พร้อมใช้งานแล้ว")
        else:
            bot.send_message(chat_id=chat_id, text=f"คุณพิมพ์ว่า: {message}")

        return "ok"
    except Exception as e:
        logging.error(f"Error in webhook: {e}")
        return "error", 500

# --- DEFAULT ROUTE ---
@app.route('/')
def index():
    return "TKC Assistant is running!"

# --- SET WEBHOOK ON SERVER START ---
if __name__ == '__main__':
    try:
        bot.delete_webhook()
        bot.set_webhook(url=FULL_WEBHOOK_URL)
        logging.info(f"✅ Webhook ถูกตั้งที่: {FULL_WEBHOOK_URL}")
    except Exception as e:
        logging.error(f"❌ ไม่สามารถตั้ง webhook ได้: {e}")

    app.run(host="0.0.0.0", port=8080)
