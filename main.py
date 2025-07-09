import os
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Dispatcher

TOKEN = os.environ.get("BOT_TOKEN") or "ใส่โทเคนตรงนี้ก็ได้ถ้าไม่ใช้ .env"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # เช่น https://your-bot-name.onrender.com/webhook

app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()
dispatcher: Dispatcher = application

# --- คำสั่งเริ่มต้น /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("สวัสดีครับ! ผมคือ TKC Assistant พร้อมใช้งานแล้ว 🐶")

# --- คำสั่ง /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ใช้คำสั่ง /start หรือพิมพ์ข้อความมาคุยกับผมได้เลยครับ")

# --- ใส่ Handler
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))

# --- Webhook Endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

# --- Root test
@app.route("/", methods=["GET"])
def home():
    return "TKC Bot is running via Webhook (Flask)", 200

if __name__ == '__main__':
    import telegram
    bot = telegram.Bot(token=TOKEN)
    bot.set_webhook(url=WEBHOOK_URL + "/webhook")
    print("Webhook set!")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
