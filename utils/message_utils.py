import os
import requests

def get_telegram_token():
    """
    คืนค่า Telegram Bot Token จาก environment variable
    """
    return os.getenv("TELEGRAM_TOKEN")

def send_message(chat_id, text, parse_mode=None):
    """
    ส่งข้อความไปที่ Telegram Chat
    - chat_id: รหัสแชท (int หรือ str)
    - text: ข้อความ (string)
    - parse_mode: "HTML", "Markdown" (หรือ None)
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
    - chat_id: รหัสแชท
    - photo_url: URL ของรูป
    - caption: ข้อความใต้รูป (string หรือ None)
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
    ส่งปุ่มขอ Location ไปให้ผู้ใช้กดแชร์ location ผ่าน Telegram
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
