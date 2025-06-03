from flask import Flask, request
import requests
import os

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_TOKEN")
GPT_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_input = data["message"]["text"]

        if user_input.startswith("/start"):
            send_message(chat_id, "สวัสดีครับ นี่คือ TKC Assistant พร้อมช่วยเหลือคุณแล้วครับ")
        else:
            # ตอบกลับจาก GPT หรือระบบเสริมอื่นๆ
            send_message(chat_id, "คุณพิมพ์ว่า: " + user_input)

    return "OK", 200

@app.route('/')
def index():
    return "TKC Assistant is running.", 200
