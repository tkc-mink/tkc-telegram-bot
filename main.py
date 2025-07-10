import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher
import logging

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

# --- Setup ---
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# --- Basic route ---
@app.route("/")
def index():
    return "TKC Assistant is running!"

# --- Webhook route ---
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        message = update.message.text

        if message == "/start":
            bot.send_message(chat_id=update.effective_chat.id, text="🎉 สวัสดีครับ! บอท TKC Assistant พร้อมใช้งานแล้ว")
        else:
            bot.send_message(chat_id=update.effective_chat.id, text=f"คุณพิมพ์ว่า: {message}")

        return "OK"
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "error", 500

# --- ตั้ง webhook ---
@app.before_first_request
def set_webhook():
    bot.delete_webhook()
    bot.set_webhook(url=FULL_WEBHOOK_URL)

# --- รัน Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
