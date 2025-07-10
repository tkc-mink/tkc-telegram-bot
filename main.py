from flask import Flask, request
import os
import telegram
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telegram.Bot(token=BOT_TOKEN)

app = Flask(__name__)

@app.route('/')
def index():
    return 'Telegram bot is running.'

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text

    # ตัวอย่างตอบกลับ
    bot.send_message(chat_id=chat_id, text="คุณพิมพ์ว่า: " + text)

    return 'ok'
