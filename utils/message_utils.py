import os
import requests

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

def send_photo(chat_id, photo_url, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json=payload,
            timeout=10
        )
    except Exception as e:
        print(f"[send_photo] {e}")

def ask_for_location(chat_id, text="📍 กรุณาแชร์ตำแหน่งของคุณ"):
    keyboard = {
        "keyboard": [
            [ {"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True} ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    }
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"[ask_for_location] {e}")
