import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

# โหลดตัวแปรจาก .env หรือ Environment ของ Render
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = APP_URL + WEBHOOK_PATH

app = Flask(__name__)

# ตั้งค่า Webhook อัตโนมัติเมื่อรันเซิร์ฟเวอร์
@app.before_first_request
def setup_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    response = requests.get(url)
    print("Setting webhook:", response.json())

# เส้นทางที่ Telegram จะเรียกมา
@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    if request.method == "POST":
        data = request.get_json()

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            message_text = data["message"].get("text", "")

            reply_text = handle_message(message_text)
            send_message(chat_id, reply_text)

    return "ok", 200

# ฟังก์ชันตอบข้อความ
def handle_message(text):
    return f"คุณพิมพ์ว่า: {text}"

# ฟังก์ชันส่งข้อความกลับไปที่ Telegram
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

# สำหรับรันทดสอบ (เช่น local)
@app.route("/", methods=["GET"])
def index():
    return "Bot is running."

# เงื่อนไขสำหรับรันผ่าน gunicorn หรือ flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
