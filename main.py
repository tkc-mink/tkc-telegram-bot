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

def handle_message(text):
    return f"คุณพิมพ์ว่า: {text}"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

# ✅ ตั้งค่า Webhook อัตโนมัติเมื่อเริ่มรัน
@app.before_first_request
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.get(url, params={"url": WEBHOOK_URL})
    print("Set webhook response:", response.text)

if __name__ == "__main__":
    app.run(debug=False)
