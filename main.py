
from flask import Flask, request
import requests
import os

app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

@app.route("/", methods=["GET"])
def index():
    return "TKC Bot is running.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("📥 DATA:", data)

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            print(f"👤 Received from {chat_id}: {text}")
            reply = generate_reply(text)
            send_message(chat_id, reply)

        return "OK", 200
    except Exception as e:
        print("❌ Error in webhook:", e)
        return "Error", 500

def generate_reply(text):
    text = text.lower()
    if "สวัสดี" in text:
        return "สวัสดีครับ 😊 มีอะไรให้ช่วยไหมครับ"
    elif "ช่วย" in text:
        return "พิมพ์ 'เมนู' เพื่อดูสิ่งที่ทำได้ครับ"
    elif "ขอบคุณ" in text:
        return "ด้วยความยินดีครับ 🙏"
    else:
        return f"คุณพิมพ์ว่า: {text}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        print("📤 Sending:", payload)
        res = requests.post(url, json=payload)
        print("✅ Telegram Response:", res.status_code, res.text)
    except Exception as e:
        print("❌ Send Error:", e)
