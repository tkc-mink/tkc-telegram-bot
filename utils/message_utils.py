# utils/message_utils.py
# -*- coding: utf-8 -*-
"""
Thin wrapper ที่เข้ากับโค้ดเดิม แต่ใต้ท้องใช้ utils.telegram_api
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- ไม่ raise error ถ้า token ไม่มี (จะ log แล้ว return เฉย ๆ)
- พิมพ์ดีบักฝั่ง telegram_api อยู่แล้ว เห็น status/resp ชัด
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import json

# ใช้ตัวส่งข้อความหลักที่มีดีบัก
from utils.telegram_api import (
    send_message as tg_send_message,
    send_photo   as tg_send_photo,
)

def _get_token() -> str:
    """คืนค่า token จาก ENV (รองรับสองชื่อ) — ใช้สำหรับ log/info เท่านั้น"""
    return (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("TELEGRAM_TOKEN")
        or ""
    ).strip()

def _log(tag: str, **kw):
    print(f"[message_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))

def send_message(chat_id: int | str, text: str, parse_mode: Optional[str] = None) -> None:
    """
    ส่งข้อความไป Telegram (ผ่าน utils.telegram_api)
    - ปลอดภัยต่อความยาวข้อความ (ตัดที่ 4096)
    - รองรับ parse_mode ("HTML"/"MarkdownV2") ถ้าต้องการ
    """
    token = _get_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, text_preview=text[:60])
        return
    payload_text = (text or "")[:4096]
    reply_markup = None  # เผื่ออนาคตจะขยายพารามิเตอร์
    # telegram_api จะพิมพ์ status/resp ให้เอง
    tg_send_message(chat_id, payload_text, reply_markup=reply_markup)

def send_photo(chat_id: int | str, photo_url: str, caption: Optional[str] = None) -> None:
    """
    ส่งรูป (ผ่าน utils.telegram_api)
    - จำกัด caption ตามข้อกำหนด Telegram
    """
    token = _get_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, photo=photo_url[:80])
        return
    cap = (caption or "")[:1024]
    tg_send_photo(chat_id, photo_url, caption=cap)

def ask_for_location(chat_id: int | str, text: str = "📍 กรุณาแชร์ตำแหน่งของคุณ") -> None:
    """
    ส่งปุ่มขอ Location ให้ผู้ใช้กดแชร์ location
    """
    token = _get_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, action="ask_for_location")
        return
    keyboard: Dict[str, Any] = {
        "keyboard": [
            [{"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    # ใช้ tg_send_message ตรง ๆ พร้อม reply_markup
    # (ฟังก์ชันต้นทางรองรับ reply_markup อยู่แล้ว)
    from utils.telegram_api import _api_post  # ใช้ low-level เพื่อส่ง reply_markup ได้
    _api_post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard,
        "parse_mode": "HTML",
    })
