import os
import logging
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# โหลดค่า .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")  # เช่น https://tkc-telegram-bot.onrender.com
WEBHOOK_PATH = "/webhook"      # หรือจะเปลี่ยน path ก็ได้ เช่น /tkc-webhook

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram bot setup
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Handler พื้นฐาน ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("สวัสดีครับ 🙏 บอทกลุ่มตระกูลชัยพร้อมใช้งานแล้ว!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f"คุณพิมพ์ว่า: {user_message}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Webhook endpoint ---
@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

# --- Set Webhook เมื่อเริ่มต้น (ครั้งเดียว) ---
@app.before_first_request
def init_webhook():
    full_url = f"{APP_URL}{WEBHOOK_PATH}"
    telegram_app.bot.set_webhook(url=full_url)
    logger.info(f"✅ Webhook ถูกตั้งเรียบร้อยที่: {full_url}")

# --- รัน Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
