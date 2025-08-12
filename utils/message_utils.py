# utils/message_utils.py
# -*- coding: utf-8 -*-
"""
Thin wrapper ที่เข้ากับโค้ดเดิม แต่ใต้ท้องใช้ utils.telegram_api
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- มี get_telegram_token() แบบ public เพื่อความเข้ากันได้กับโค้ดเดิม
- รองรับ parse_mode ("HTML" / "Markdown" / "MarkdownV2") อย่างถูกต้อง
- ไม่ raise error ถ้า token ไม่มี (log แล้ว return เฉย ๆ)
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import json

# ฟังก์ชันระดับล่างจาก telegram_api (มี log ดีบักให้แล้ว)
from utils.telegram_api import (
    send_message as tg_send_message,
    send_photo as tg_send_photo,
)
from utils.telegram_api import _api_post  # ใช้เมื่อจำเป็นต้องระบุพารามิเตอร์เอง

ALLOWED_PARSE = {"HTML", "Markdown", "MarkdownV2"}


# ===== Token helpers =====
def get_telegram_token() -> str:
    """
    คืนค่า Telegram Bot Token จาก ENV (รองรับ TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN)
    - มีไว้ให้โมดูลอื่น import ได้ (ความเข้ากันได้กับโค้ดเก่า)
    """
    tok = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_TOKEN")
        or ""
    ).strip()
    if not tok:
        print("[message_utils] WARNING: Telegram token not set in TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
    return tok


def _log(tag: str, **kw):
    print(f"[message_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))


# ===== High-level senders =====
def send_message(
    chat_id: int | str,
    text: str,
    parse_mode: Optional[str] = None,
) -> None:
    """
    ส่งข้อความไป Telegram
    - จำกัดความยาวที่ 4096 ตัวอักษร
    - ถ้าไม่ระบุ parse_mode หรือเป็น "HTML" จะใช้ tg_send_message (ซึ่ง default เป็น HTML)
    - ถ้าระบุ parse_mode อื่น จะเรียกผ่าน _api_post เพื่อส่งค่า parse_mode ให้ถูกต้อง
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, text_preview=(text or "")[:80])
        return

    safe_text = (text or "")[:4096]
    try:
        if parse_mode and parse_mode in ALLOWED_PARSE and parse_mode != "HTML":
            # ระบุ parse_mode ที่แตกต่างจากค่า default
            _api_post("sendMessage", {
                "chat_id": chat_id,
                "text": safe_text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
        else:
            # ใช้ helper ปกติ (default เป็น HTML อยู่แล้วใน telegram_api)
            tg_send_message(chat_id, safe_text, reply_markup=None)
    except Exception as e:
        _log("ERROR_SEND_MESSAGE", err=str(e))


def send_photo(
    chat_id: int | str,
    photo_url: str,
    caption: Optional[str] = None,
) -> None:
    """
    ส่งรูปภาพไป Telegram
    - จำกัด caption ~1024 ตัวอักษรตามข้อกำหนด Telegram
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, photo=photo_url[:120])
        return

    cap = (caption or "")[:1024]
    try:
        tg_send_photo(chat_id, photo_url, caption=cap)
    except Exception as e:
        _log("ERROR_SEND_PHOTO", err=str(e))


def ask_for_location(
    chat_id: int | str,
    text: str = "📍 กรุณาแชร์ตำแหน่งของคุณ",
) -> None:
    """
    ส่งปุ่มขอ Location ให้ผู้ใช้กดแชร์ location
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, action="ask_for_location")
        return

    keyboard: Dict[str, Any] = {
        "keyboard": [[{"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }
    try:
        _api_post("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
            "parse_mode": "HTML",
        })
    except Exception as e:
        _log("ERROR_ASK_LOCATION", err=str(e))
