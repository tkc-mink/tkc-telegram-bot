import os
import logging
import asyncio
from flask import Flask, request
from telegram import Bot, Update

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# ENV config
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

# Telegram Bot
bot = Bot(token=BOT_TOKEN)

@app.route("/")
def index():
    return "TKC Telegram Bot is running."

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        if update.message:
            chat_id = update.message.chat_id
            text = update.message.text

            if text == "/start":
                bot.send_message(chat_id=chat_id, text="สวัสดีครับ 👋 ยินดีต้อนรับสู่ระบบใช้งานบอท!")
            else:
                bot.send_message(chat_id=chat_id, text=f"คุณพิมพ์ว่า: {text}")
        return "ok"
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return "error", 500

async def set_webhook():
    try:
        await bot.set_webhook(FULL_WEBHOOK_URL)
        logger.info(f"✅ Webhook ถูกตั้งแล้วที่: {FULL_WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ ตั้ง Webhook ไม่สำเร็จ: {e}")

if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=8080)
