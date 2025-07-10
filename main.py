from flask import Flask, request
import requests
import os

app = Flask(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}"

@app.route("/", methods=["GET"])
def index():
    return "TKC Telegram Bot is running.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("DATA RECEIVED:", data)

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            print(f"Received message: {text} from chat_id: {chat_id}")

            reply_text = generate_reply(text)
            send_message(chat_id, reply_text)

        return "OK", 200
    except Exception as e:
        print("Webhook error:", e)
        return "Error", 500

def generate_reply(text):
    text = text.lower()
    if "สวัสดี" in text:
        return "สวัสดีครับ ยินดีต้อนรับสู่ระบบ TKC Bot ครับ"
    elif "ช่วย" in text:
        return "พิมพ์คำว่า 'เมนู' เพื่อดูสิ่งที่ TKC Assistant คุยได้ครับ"
    elif "ขอบคุณ" in text:
        return "ยินดีเสมอครับ 😊"
    else:
        return f"คุณพิมพ์ว่า: {text}"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        print("Sending message:", payload)
        response = requests.post(url, json=payload)
        print("Response status:", response.status_code, "Text:", response.text)

        if response.status_code != 200:
            print("Failed to send message:", response.text)
    except Exception as e:
        print("Exception during sending message:", e)
