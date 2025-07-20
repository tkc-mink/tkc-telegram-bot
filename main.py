import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
import openai

from handlers import handle_message, start_command
from location_handler import handle_location
from history_handler import log_user_message

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

# Register handlers
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(MessageHandler(filters.LOCATION, handle_location))
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Define webhook route
@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
    return "OK"

# Set webhook when server starts
@app.before_first_request
def setup_webhook():
    from telegram import Bot
    bot = Bot(BOT_TOKEN)
    bot.set_webhook(WEBHOOK_URL + "/webhook")
    print("✅ Webhook set!")

# Run Flask App
if __name__ == "__main__":
    app.run(port=8080)
