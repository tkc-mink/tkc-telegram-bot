import os
import telebot
from flask import Flask, request
from dotenv import load_dotenv

# โหลดค่าจาก .env (กรณีทดสอบในเครื่อง)
load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

# ตรวจสอบความพร้อมของ token
if not API_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ฟังก์ชันทักทาย
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! ผมคือบอทของ TKC พร้อมให้บริการครับ 😊")

# ตัวอย่างฟังก์ชันโต้ตอบอื่น ๆ
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"คุณพิมพ์ว่า: {message.text}")

# Webhook Endpoint
@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        except Exception as e:
            return f"Error: {str(e)}", 400
    else:
        return 'Unsupported Media Type', 415

# สำหรับระบบภายนอก (ping เช็คว่า App ยังทำงานอยู่)
@app.route("/", methods=['GET'])
def index():
    return "✅ Bot is running and ready to receive webhook.", 200

# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
