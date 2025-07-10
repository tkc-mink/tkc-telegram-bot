import os
import logging
from dotenv import load_dotenv
from flask import Flask, request
import telegram

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = telegram.Bot(token=BOT_TOKEN)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

@app.route("/")
def index():
    return "TKC Telegram Bot is running."

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update.message:
            chat_id = update.message.chat_id
            text = update.message.text
            if text == "/start":
                bot.send_message(chat_id=chat_id, text="สวัสดีครับ 🙏 บอทกลุ่มตระกูลชัยพร้อมใช้งานแล้ว!")
            else:
                bot.send_message(chat_id=chat_id, text=f"คุณพิมพ์ว่า: {text}")
        return "ok"
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "error", 500

def set_webhook():
    try:
        bot.set_webhook(FULL_WEBHOOK_URL)
        logger.info(f"✅ Webhook ถูกตั้งแล้วที่: {FULL_WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ ตั้ง Webhook ไม่สำเร็จ: {e}")

if __name__ == "__main__":
    set_webhook()
    app.run(host="0.0.0.0", port=8080)
