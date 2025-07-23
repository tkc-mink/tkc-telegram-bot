# utils/message_utils.py

import os
import requests

def get_telegram_token():
    return os.getenv("TELEGRAM_TOKEN")

def send_message(chat_id, text, parse_mode=None):
    """
    ส่งข้อความไปที่ Telegram Chat (รองรับ Markdown/HTML)
    """
    try:
        payload = {
            "chat_id": chat_id,
            "text": text[:4096]
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        requests.post(
            f"https://api.telegram.org/bot{get_telegram_token()}/sendMessage",
            json=payload,
            timeout=10
        )
    except Exception as e:
        print(f"[send_message] {e}")

def send_photo(chat_id, photo_url, caption=None):
    """
    ส่งรูปภาพไปที่ Telegram Chat
    """
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    try:
        requests.post(
            f"https://api.telegram.org/bot{get_telegram_token()}/sendPhoto",
            json=payload,
            timeout=10
        )
    except Exception as e:
        print(f"[send_photo] {e}")

def ask_for_location(chat_id, text="📍 กรุณาแชร์ตำแหน่งของคุณ"):
    """
    ขอให้ผู้ใช้แชร์ location (โชว์ปุ่ม Telegram)
    """
    keyboard = {
        "keyboard": [
            [{"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True}]
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
            f"https://api.telegram.org/bot{get_telegram_token()}/sendMessage",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"[ask_for_location] {e}")
