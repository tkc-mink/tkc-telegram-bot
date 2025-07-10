from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ดึง TOKEN จาก Environment Variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route("/")
def home():
    return "TKC Telegram Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json()
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            reply_text = generate_reply(text)
            send_message(chat_id, reply_text)
        return "OK", 200
    else:
        return "Method Not Allowed", 405

def generate_reply(text):
    # โต้ตอบแบบพื้นฐานสำหรับทดสอบระบบ
    text = text.lower()
    if "สวัสดี" in text:
        return "สวัสดีครับ ยินดีต้อนรับสู่ระบบ TKC Bot ครับ"
    elif "ชื่ออะไร" in text:
        return "ผมคือ TKC Assistant ครับผม"
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
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print("Error sending message:", response.text)
    except Exception as e:
        print("Exception during sending message:", e)

if __name__ == "__main__":
    app.run(debug=True)
