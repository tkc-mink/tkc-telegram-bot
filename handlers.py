import requests
import os

def handle_message(data):
    try:
        message = data.get("message", {})
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        token = os.getenv("BOT_TOKEN")

        reply = f"คุณพิมพ์ว่า: {text}"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": reply
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"handle_message error: {e}")