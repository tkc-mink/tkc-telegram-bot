# utils/telegram_api.py
# -*- coding: utf-8 -*-
"""
Thin wrapper สำหรับ Telegram Bot API (Upgraded with location request)
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- Log ดีบักชัดเจน
- ✅ เพิ่มฟังก์ชัน ask_for_location
"""
from __future__ import annotations
import os
import json
import requests
import re
from typing import Any, Dict, Optional

# ===== ENV / CONFIG =====
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or ""
).strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
TIMEOUT = float(os.getenv("TG_API_TIMEOUT", "10"))

# (ส่วนของ _log_debug, _api_post, _api_get, _NO_ECHO_PREFIXES, _should_block_no_echo คงไว้เหมือนเดิม)
def _log_debug(tag: str, **kw):
    print(f"[telegram_api] {tag} :: " + json.dumps(kw, ensure_ascii=False))

def _api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    if not BOT_TOKEN:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        data = r.json() if r.content else {"ok": r.ok, "status_code": r.status_code}
        # _log_debug("POST", path=path, status=r.status_code, resp=data) # Comment out for cleaner logs
        return data
    except Exception as e:
        print(f"[telegram_api] POST error:", e)
        return None

def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | None:
    if not BOT_TOKEN:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.get(url, params=params or {}, timeout=TIMEOUT)
        data = r.json() if r.content else {"ok": r.ok, "status_code": r.status_code}
        # _log_debug("GET", path=path, status=r.status_code, resp=data) # Comment out for cleaner logs
        return data
    except Exception as e:
        print("[telegram_api] GET error:", e)
        return None

_NO_ECHO_PREFIXES = re.compile("|".join([
    r"^\s*รับทราบ(?:ครับ|ค่ะ|นะ)?[:：-]\s*", r"^\s*คุณ\s*ถามว่า[:：-]\s*",
    r"^\s*สรุปคำถาม[:：-]\s*", r"^\s*ยืนยันคำถาม[:：-]\s*",
    r"^\s*คำถามของคุณ[:：-]\s*", r"^\s*Question[:：-]\s*", r"^\s*You\s+asked[:：-]\s*",
]), re.IGNORECASE | re.UNICODE)

def _should_block_no_echo(text: str) -> bool:
    if not text or "\n" in text: return False
    return bool(_NO_ECHO_PREFIXES.match(text))

# ===== Core helpers =====
def send_message(
    chat_id: int | str, text: str, reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None, disable_web_page_preview: bool = True
):
    if _should_block_no_echo(text or ""):
        _log_debug("BLOCK_NO_ECHO", chat_id=chat_id, preview=(text or "")[:120])
        return None
    payload: Dict[str, Any] = {
        "chat_id": chat_id, "text": (text or "")[:4096],
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup: payload["reply_markup"] = reply_markup
    if parse_mode: payload["parse_mode"] = parse_mode
    return _api_post("sendMessage", payload)

# --- ✅ ฟังก์ชันที่เราเพิ่มเข้ามา ---
def ask_for_location(chat_id: int | str, text: str):
    """
    ส่งข้อความพร้อมปุ่ม 'Share Location'
    """
    print(f"[telegram_api] Asking for location from chat_id: {chat_id}")
    # สร้างปุ่มที่เมื่อกดแล้วจะให้ user แชร์ตำแหน่ง
    location_keyboard = {
        "keyboard": [[{
            "text": "📍 แชร์ตำแหน่งปัจจุบัน",
            "request_location": True
        }]],
        "one_time_keyboard": True, # ให้ปุ่มหายไปหลังจากกด
        "resize_keyboard": True
    }
    # ส่งข้อความพร้อมปุ่มนี้
    return send_message(
        chat_id,
        text=text,
        reply_markup=location_keyboard
    )

def send_chat_action(chat_id: int | str, action: str = "typing"):
    return _api_post("sendChatAction", {"chat_id": chat_id, "action": action})

# (ส่วนที่เหลือของไฟล์เหมือนเดิมทุกประการ)
def send_photo(
    chat_id: int | str, photo_url_or_file_id: str, caption: str | None = None,
    reply_markup: Dict[str, Any] | None = None, parse_mode: Optional[str] = None
):
    payload: Dict[str, Any] = {"chat_id": chat_id, "photo": photo_url_or_file_id}
    if caption is not None: payload["caption"] = caption[:1024]
    if reply_markup: payload["reply_markup"] = reply_markup
    if parse_mode: payload["parse_mode"] = parse_mode
    return _api_post("sendPhoto", payload)

def edit_message_text(
    chat_id: int | str, message_id: int, text: str,
    reply_markup: Dict[str, Any] | None = None, parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True
):
    payload: Dict[str, Any] = {
        "chat_id": chat_id, "message_id": message_id, "text": (text or "")[:4096],
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup: payload["reply_markup"] = reply_markup
    if parse_mode: payload["parse_mode"] = parse_mode
    return _api_post("editMessageText", payload)

def answer_callback_query(callback_query_id: str, text: str | None = None, show_alert: bool = False):
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text: payload["text"] = text
    return _api_post("answerCallbackQuery", payload)

def set_webhook(url: str, drop_pending: bool = True, secret_token: Optional[str] = None):
    params: Dict[str, Any] = {
        "url": url, "allowed_updates": ["message", "edited_message", "callback_query"],
        "drop_pending_updates": drop_pending,
    }
    if secret_token: params["secret_token"] = secret_token
    return _api_post("setWebhook", params)

def delete_webhook(drop_pending: bool = True):
    return _api_post("deleteWebhook", {"drop_pending_updates": drop_pending})

def get_webhook_info():
    return _api_get("getWebhookInfo")

def get_me():
    return _api_get("getMe")

def inline_rating_keyboard():
    rows = [[{"text": str(i), "callback_data": f"review:{i}"} for i in range(1, 6)]]
    return {"inline_keyboard": rows}

def reply_keyboard(rows: list[list[str]], one_time: bool = True, resize: bool = True):
    return {
        "keyboard": [[{"text": t} for t in row] for row in rows],
        "one_time_keyboard": one_time,
        "resize_keyboard": resize,
    }
