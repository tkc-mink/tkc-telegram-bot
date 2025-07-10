import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", APP_URL + WEBHOOK_PATH)

app = Flask(__name__)

# เรียกตั้งค่า webhook ทันทีหลังสร้างแอป
with app.app_context():
    try:
        set_webhook()
    except Exception as e:
        print("❌ Set webhook failed:", e)

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    
    data = request.get_json()
    print("🔁 Incoming data:", data)  # เพิ่มบรรทัดนี้
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        message_text = data["message"].get("text", "")
        print("📨 Got message:", message_text)  # เพิ่มบรรทัดนี้
        reply_text = handle_message(message_text)
        send_message(chat_id, reply_text)
    return "ok", 200

def handle_message(text):
    return f"คุณพิมพ์ว่า: {text}"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

# ✅ เงื่อนไขนี้จะทำงานเมื่อใช้ `python main.py` (สำหรับ local หรือ debug เท่านั้น)
if __name__ == "__main__":
    set_webhook()
    app.run(debug=False)

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {
        "url": WEBHOOK_URL
    }
    response = requests.post(url, json=payload)
    print("🚀 Set webhook response:", response.text)
