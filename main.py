import os
from flask import Flask, request
import telebot
from dotenv import load_dotenv

# โหลดตัวแปรจาก .env
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- ส่วนที่ Telegram ส่งข้อมูลมาที่เซิร์ฟเวอร์เราผ่าน webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid content type', 403

# --- คำสั่งหลักของ Bot ---
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, f"คุณพิมพ์ว่า: {message.text}")

# --- ตั้ง webhook เมื่อแอปรันครั้งแรก ---
@app.before_first_request
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

# --- รัน Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
