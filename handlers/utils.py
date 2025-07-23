# handlers/utils.py
import requests
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096]},
            timeout=10
        )
    except Exception as e:
        print(f"[send_message] {e}")
