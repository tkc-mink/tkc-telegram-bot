import telebot
import os
from flask import Flask, request

# โหลด Token และ Webhook URL จาก .env หรือ Environment Variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# สร้างตัว bot และ app
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================
# ส่วนตอบกลับข้อความ
# =========================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ! ยินดีต้อนรับเข้าสู่ระบบบอท Telegram ของกลุ่มตระกูลชัย")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"คุณพิมพ์ว่า: {message.text}")

# =========================
# ตั้งค่า webhook
# =========================
@app.before_first_request
def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

# =========================
# รับ webhook จาก Telegram
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'ok', 200

# =========================
# รัน Flask app
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
