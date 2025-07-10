import os
import telebot
from flask import Flask, request

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================
# Handler พื้นฐาน
# =========================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับ ผมคือบอทของกลุ่มตระกูลชัย พร้อมรับใช้ครับ")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, f"คุณพิมพ์ว่า: {message.text}")

# =========================
# Webhook Endpoint
# =========================
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return 'ok', 200

# =========================
# Run Flask App + Set Webhook
# =========================
if __name__ == "__main__":
    # ตั้งค่า webhook ที่นี่ (เพราะ before_first_request ใช้ไม่ได้ใน Render)
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

    # รัน Flask App (สำหรับ Local Testing หรือ Render Web Service)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
