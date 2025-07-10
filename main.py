import os
from flask import Flask, request
import telebot
from dotenv import load_dotenv

# โหลดค่าตัวแปรจาก .env หรือ Environment บน Render
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH") or "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"{os.getenv('APP_URL')}{WEBHOOK_PATH}"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ฟังก์ชันรับข้อความจาก Telegram
@bot.message_handler(commands=["start"])
def handle_start(message):
    bot.reply_to(message, "สวัสดีครับ! บอทพร้อมใช้งานแล้ว 🎉")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, f"คุณพิมพ์ว่า: {message.text}")

# Flask route สำหรับ Webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Invalid content-type", 403

# ตั้งค่า Webhook ตอนเริ่มระบบ
if __name__ == "__main__":
    # เคลียร์ webhook เก่าก่อน (เผื่อเคยตั้งไว้แล้ว)
    bot.remove_webhook()

    # ตั้งค่า webhook ใหม่
    bot.set_webhook(url=WEBHOOK_URL)

    # รัน Flask app
    app.run(host="0.0.0.0", port=5000)
