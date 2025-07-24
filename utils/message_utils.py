# utils/message_utils.py

import os
import requests
from typing import Optional

def get_telegram_token() -> str:
    """
    คืนค่า Telegram Bot Token จาก environment variable (ต้องชื่อ TELEGRAM_TOKEN)
    """
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise EnvironmentError("ไม่พบ TELEGRAM_TOKEN ใน environment variable")
    return token

def send_message(chat_id: int, text: str, parse_mode: Optional[str] = None) -> None:
    """
    ส่งข้อความไปที่ Telegram Chat
    - chat_id: รหัสแชท (int หรือ str)
    - text: ข้อความ (string)
    - parse_mode: "HTML", "Markdown" หรือ None
    """
    try:
        payload = {
            "chat_id": chat_id,
            "text": text[:4096],  # จำกัดความยาวข้อความสูงสุดที่ Telegram รองรับ
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        resp = requests.post(
            f"https://api.telegram.org/bot{get_telegram_token()}/sendMessage",
            json=payload,
            timeout=10
        )
        if not resp.ok:
            print(f"[send_message] Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[send_message] {e}")

def send_photo(chat_id: int, photo_url: str, caption: Optional[str] = None) -> None:
    """
    ส่งรูปภาพไปที่ Telegram Chat
    - chat_id: รหัสแชท (int หรือ str)
    - photo_url: URL ของรูป
    - caption: ข้อความใต้รูป (string หรือ None)
    """
    try:
        payload = {"chat_id": chat_id, "photo": photo_url}
        if caption:
            payload["caption"] = caption[:1024]  # จำกัด caption ตามที่ Telegram กำหนด
        resp = requests.post(
            f"https://api.telegram.org/bot{get_telegram_token()}/sendPhoto",
            json=payload,
            timeout=10
        )
        if not resp.ok:
            print(f"[send_photo] Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[send_photo] {e}")

def ask_for_location(chat_id: int, text: str = "📍 กรุณาแชร์ตำแหน่งของคุณ") -> None:
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
        resp = requests.post(
            f"https://api.telegram.org/bot{get_telegram_token()}/sendMessage",
            json=payload,
            timeout=10
        )
        if not resp.ok:
            print(f"[ask_for_location] Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[ask_for_location] {e}")
