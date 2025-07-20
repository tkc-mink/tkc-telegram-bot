import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import openai

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Env Variables from Render (already set)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Setup OpenAI
openai.api_key = OPENAI_API_KEY

# Create Flask app
app = Flask(__name__)

# Create Telegram App
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("สวัสดีครับ! พิมพ์คำถามมาได้เลยนะครับ 😊")

# Handle Message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "คุณเป็นผู้ช่วยขององค์กรชื่อ TKC Assistant"},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        await update.message.reply_text("ขออภัยครับ ระบบไม่สามารถตอบได้ในขณะนี้ 🙇")

# Register Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return 'OK'

# Set webhook when run
@app.before_first_request
def set_webhook():
    telegram_app.bot.set_webhook(WEBHOOK_URL)

if __name__ == '__main__':
    app.run(port=5000)
