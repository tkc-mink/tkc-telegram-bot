import os
import logging
import asyncio
from flask import Flask, request
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")  # เช่น https://ชื่อโดเมน.onrender.com
WEBHOOK_PATH = "/webhook"
FULL_WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

bot = AsyncTeleBot(BOT_TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        await bot.process_new_updates([update])
        return "ok", 200
    except Exception as e:
        logging.error(f"❌ Error in webhook: {e}")
        return "error", 500

@app.route("/")
def index():
    return "✅ TKC Assistant is alive!"

@bot.message_handler(commands=["start"])
async def handle_start(message):
    await bot.send_message(message.chat.id, "🎉 สวัสดีครับ! บอท TKC Assistant พร้อมใช้งานแล้ว")

@bot.message_handler(func=lambda m: True)
async def handle_all(message):
    await bot.send_message(message.chat.id, f"คุณพิมพ์ว่า: {message.text}")

async def setup_webhook():
    await bot.delete_webhook()
    await bot.set_webhook(url=FULL_WEBHOOK_URL)
    logging.info(f"✅ Webhook ตั้งค่าแล้วที่: {FULL_WEBHOOK_URL}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
    app.run(host="0.0.0.0", port=8080)
