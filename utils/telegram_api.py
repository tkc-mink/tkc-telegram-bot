# utils/telegram_api.py
# -*- coding: utf-8 -*-
"""
Thin wrapper สำหรับ Telegram Bot API
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- Log ดีบักชัดเจน
- ไม่บังคับ parse_mode โดยดีฟอลต์ (กัน 400 can't parse entities)
"""

from __future__ import annotations
import os
import json
import requests
from typing import Any, Dict, Optional

# ===== ENV / CONFIG =====
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or ""
).strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
TIMEOUT = float(os.getenv("TG_API_TIMEOUT", "10"))

def _log_debug(tag: str, **kw):
    print(f"[telegram_api] {tag} :: " + json.dumps(kw, ensure_ascii=False))

def _api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    if not BOT_TOKEN:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        _log_debug("POST", path=path, status=r.status_code, resp=data)
        return data
    except Exception as e:
        print("[telegram_api] POST error:", e)
        return None

def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | None:
    if not BOT_TOKEN:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.get(url, params=params or {}, timeout=TIMEOUT)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text}
        _log_debug("GET", path=path, status=r.status_code, resp=data)
        return data
    except Exception as e:
        print("[telegram_api] GET error:", e)
        return None

# ===== Core helpers =====
def send_message(
    chat_id: int | str,
    text: str,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,           # <-- ทำเป็นออปชัน
    disable_web_page_preview: bool = True,
):
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:                               # <-- ใส่เฉพาะเมื่อผู้เรียกต้องการจริง
        payload["parse_mode"] = parse_mode
    return _api_post("sendMessage", payload)

def send_chat_action(chat_id: int | str, action: str = "typing"):
    return _api_post("sendChatAction", {"chat_id": chat_id, "action": action})

def send_photo(
    chat_id: int | str,
    photo_url_or_file_id: str,
    caption: str | None = None,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,            # <-- ทำเป็นออปชัน
):
    payload: Dict[str, Any] = {"chat_id": chat_id, "photo": photo_url_or_file_id}
    if caption is not None:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return _api_post("sendPhoto", payload)

def edit_message_text(
    chat_id: int | str,
    message_id: int,
    text: str,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,            # <-- ทำเป็นออปชัน
    disable_web_page_preview: bool = True,
):
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return _api_post("editMessageText", payload)

def answer_callback_query(callback_query_id: str, text: str | None = None, show_alert: bool = False):
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    return _api_post("answerCallbackQuery", payload)

# ===== Webhook / Diagnostics =====
def set_webhook(url: str, drop_pending: bool = True, secret_token: Optional[str] = None):
    params: Dict[str, Any] = {
        "url": url,
        "allowed_updates": ["message", "edited_message", "callback_query"],
        "drop_pending_updates": drop_pending,
    }
    if secret_token:
        params["secret_token"] = secret_token
    return _api_post("setWebhook", params)

def delete_webhook(drop_pending: bool = True):
    return _api_post("deleteWebhook", {"drop_pending_updates": drop_pending})

def get_webhook_info():
    return _api_get("getWebhookInfo")

def get_me():
    return _api_get("getMe")

# ===== Convenience keyboard builders =====
def inline_rating_keyboard():
    rows = [[{"text": str(i), "callback_data": f"review:{i}"} for i in range(1, 6)]]
    return {"inline_keyboard": rows}

def reply_keyboard(rows: list[list[str]], one_time: bool = True, resize: bool = True):
    return {
        "keyboard": [[{"text": t} for t in row] for row in rows],
        "one_time_keyboard": one_time,
        "resize_keyboard": resize,
    }
