import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.constants import ParseMode
import logging

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        message = update.message.text
        chat_id = update.message.chat_id

        if message == "/start":
            asyncio.run(bot.send_message(chat_id=chat_id, text="🎉 สวัสดีครับ! บอท TKC Assistant พร้อมใช้งานแล้ว"))
        else:
            asyncio.run(bot.send_message(chat_id=chat_id, text=f"คุณพิมพ์ว่า: {message}"))

        return "ok"
    except Exception as e:
        logging.error(f"❌ Error in webhook: {e}")
        return "error", 500

@app.route('/')
def index():
    return "✅ TKC Assistant is alive!"

async def setup_webhook():
    await bot.delete_webhook()
    await bot.set_webhook(url=FULL_WEBHOOK_URL)
    logging.info(f"✅ Webhook ตั้งแล้วที่: {FULL_WEBHOOK_URL}")

if __name__ == '__main__':
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=8080)
