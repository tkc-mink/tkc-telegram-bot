import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

def handle_message(text):
    return f'คุณพิมพ์ว่า: {text}'

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📩 Incoming data:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        message_text = data["message"].get("text", "")
        print("💬 Got message:", message_text)

        reply_text = handle_message(message_text)
        send_message(chat_id, reply_text)

    return "ok", 200

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {
        "url": WEBHOOK_URL
    }
    response = requests.post(url, json=payload)
    print("🔗 Set webhook response:", response.text)

# ✅ ใช้เมื่อรันผ่าน `python main.py` (debug หรือ local เท่านั้น)
if __name__ == '__main__':
    set_webhook()
    app.run(debug=False)
