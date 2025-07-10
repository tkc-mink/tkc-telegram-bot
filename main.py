from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.route('/')
def home():
    return 'Bot is running!', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📥 Incoming data:", data)

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        message_text = data["message"].get("text", "")
        print("📨 Got message:", message_text)

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

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    payload = {
        "url": WEBHOOK_URL
    }
    response = requests.post(url, json=payload)
    print("✅ Set webhook response:", response.text)

if __name__ == "__main__":
    set_webhook()
    app.run(debug=True)
