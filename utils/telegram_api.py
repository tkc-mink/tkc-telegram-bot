# utils/telegram_api.py
# -*- coding: utf-8 -*-
"""
Thin wrapper สำหรับ Telegram Bot API (Stable & Backward-Compatible)
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- ส่งข้อความยาว: แบ่งอัตโนมัติ ≤4096 ตัวอักษร (ชิ้นแรกเท่านั้นที่แนบ reply_markup/ตอบกลับ)
- Retry อัจฉริยะ (รวมถึงเคารพ 429 retry_after) + timeout ปรับได้
- กันข้อความทวนคำถาม (no-echo) สำหรับชิ้นแรก
- รองรับ parse_mode เฉพาะที่อนุญาต (HTML / Markdown / MarkdownV2)
- มี send_photo / send_document / edit_message_text / ask_for_location / send_chat_action / set_webhook ฯลฯ

หมายเหตุ:
- โค้ดระดับสูงที่ต้อง “สวย/อัตโนมัติยิ่งกว่า” ให้ใช้ utils.message_utils (ซึ่งเรียกมาที่ wrapper นี้อีกที)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List
import os
import json
import re
import time
import requests

# ===== ENV / CONFIG =====
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or ""
).strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

TIMEOUT = float(os.getenv("TG_API_TIMEOUT", "10"))
RETRIES = int(os.getenv("TG_API_RETRIES", "1"))             # retry เพิ่มเติม (รวม=1+RETRIES)
BACKOFF_BASE = float(os.getenv("TG_API_BACKOFF_BASE", "0.4"))

TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024
ALLOWED_PARSE = {"HTML", "Markdown", "MarkdownV2"}

# ===== Internal logging =====
def _log_debug(tag: str, **kw):
    try:
        print(f"[telegram_api] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[telegram_api] {tag} :: {kw}")

def _allowed_parse_mode(pm: Optional[str]) -> Optional[str]:
    if not pm:
        return None
    return pm if pm in ALLOWED_PARSE else None

# ===== No-echo blocker =====
_NO_ECHO_PREFIXES = re.compile("|".join([
    r"^\s*รับทราบ(?:ครับ|ค่ะ|นะ)?[:：-]\s*", r"^\s*คุณ\s*ถามว่า[:：-]\s*",
    r"^\s*สรุปคำถาม[:：-]\s*", r"^\s*ยืนยันคำถาม[:：-]\s*",
    r"^\s*คำถามของคุณ[:：-]\s*", r"^\s*Question[:：-]\s*", r"^\s*You\s+asked[:：-]\s*",
]), re.IGNORECASE | re.UNICODE)

def _should_block_no_echo(text: str) -> bool:
    if not text or "\n" in text:
        return False
    return bool(_NO_ECHO_PREFIXES.match(text))

# ===== Core HTTP with retry (handles 429 retry_after) =====
def _retry_sleep(attempt: int, retry_after: Optional[float] = None):
    if retry_after is not None:
        time.sleep(min(float(retry_after), 3.0))
        return
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _request(method: str, path: str, *, json_payload: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | None:
    if not BOT_TOKEN or not API:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None

    url = f"{API}/{path.lstrip('/')}"
    last_err = None

    for attempt in range(1, RETRIES + 2):
        try:
            if method == "POST":
                r = requests.post(url, json=json_payload or {}, timeout=TIMEOUT)
            else:
                r = requests.get(url, params=params or {}, timeout=TIMEOUT)

            # 429 handling
            if r.status_code == 429:
                retry_after = None
                try:
                    j = r.json()
                    retry_after = j.get("parameters", {}).get("retry_after")
                except Exception:
                    pass
                _log_debug("HTTP_429", path=path, attempt=attempt, retry_after=retry_after)
                if attempt <= RETRIES:
                    _retry_sleep(attempt, retry_after)
                    continue

            # Best-effort parse
            data = {}
            try:
                data = r.json() if r.content else {"ok": r.ok, "status_code": r.status_code}
            except Exception:
                data = {"ok": r.ok, "status_code": r.status_code, "text": r.text[:200]}

            if r.ok:
                return data

            last_err = {"status": r.status_code, "body": (r.text[:200] if r.text else "")}
            _log_debug("HTTP_ERROR", path=path, **last_err)
            if attempt <= RETRIES:
                _retry_sleep(attempt)

        except requests.RequestException as e:
            last_err = {"err": str(e)}
            _log_debug("HTTP_EXCEPTION", path=path, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except Exception as e:
            last_err = {"err": str(e)}
            _log_debug("HTTP_UNKNOWN_ERR", path=path, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _retry_sleep(attempt)

    _log_debug("HTTP_GIVEUP", path=path, last_err=last_err)
    return None

def _api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
    return _request("POST", path, json_payload=payload)

def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | None:
    return _request("GET", path, params=params)

# ===== Split helpers =====
def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> List[str]:
    """
    แบ่งข้อความยาวเป็นหลายชิ้นให้ไม่เกิน limit โดยพยายามตัดตามบรรทัด/ช่องว่าง
    (โค้ดระดับสูงควรใช้ utils.message_utils ที่ฉลาดกว่า แต่ที่นี่ทำให้ ‘พอใช้ได้’)
    """
    text = (text or "")
    if not text:
        return [""]

    if len(text) <= limit:
        return [text]

    parts: List[str] = []
    buf: List[str] = []
    cur = 0

    for ln in text.splitlines(True):  # keep '\n'
        L = len(ln)
        if cur + L <= limit:
            buf.append(ln)
            cur += L
            continue

        if L > limit:
            if buf:
                parts.append("".join(buf))
                buf, cur = [], 0
            chunk = ln
            while len(chunk) > limit:
                parts.append(chunk[:limit])
                chunk = chunk[limit:]
            if chunk:
                buf.append(chunk)
                cur = len(chunk)
        else:
            parts.append("".join(buf))
            buf, cur = [ln], L

    if buf:
        parts.append("".join(buf))

    normalized: List[str] = []
    for p in parts:
        if len(p) <= limit:
            normalized.append(p)
            continue
        words = p.split(" ")
        cur_s, Ls = [], 0
        for w in words:
            add = w + " "
            if Ls + len(add) > limit and cur_s:
                normalized.append("".join(cur_s).rstrip())
                cur_s, Ls = [], 0
            cur_s.append(add); Ls += len(add)
        if cur_s:
            normalized.append("".join(cur_s).rstrip())

    return normalized or [""]

# ===== Public helpers =====
def send_message(
    chat_id: int | str,
    text: str,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
    reply_to_message_id: Optional[int] = None,
):
    """
    ส่งข้อความ (auto-chunk ≤4096) — แนบ reply_markup / reply_to เฉพาะชิ้นแรก
    กัน no-echo สำหรับชิ้นแรก
    """
    if not BOT_TOKEN or not API:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None

    chunks = _split_for_telegram(text or "")
    if not chunks:
        chunks = [""]

    # block เฉพาะชิ้นแรก
    if _should_block_no_echo(chunks[0]):
        _log_debug("BLOCK_NO_ECHO", chat_id=chat_id, preview=(chunks[0] or "")[:160])
        return None

    pm = _allowed_parse_mode(parse_mode)

    res = None
    for idx, chunk in enumerate(chunks):
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": chunk,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if pm: payload["parse_mode"] = pm
        if idx == 0:
            if reply_markup: payload["reply_markup"] = reply_markup
            if reply_to_message_id is not None: payload["reply_to_message_id"] = reply_to_message_id
        res = _api_post("sendMessage", payload)
    return res

def send_photo(
    chat_id: int | str,
    photo_url_or_file_id: str,
    caption: str | None = None,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
):
    payload: Dict[str, Any] = {"chat_id": chat_id, "photo": photo_url_or_file_id}
    if caption is not None:
        payload["caption"] = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = _allowed_parse_mode(parse_mode)
    if pm: payload["parse_mode"] = pm
    if reply_markup: payload["reply_markup"] = reply_markup
    if reply_to_message_id is not None: payload["reply_to_message_id"] = reply_to_message_id
    return _api_post("sendPhoto", payload)

def send_document(
    chat_id: int | str,
    file_url_or_file_id: str,
    caption: str | None = None,
    parse_mode: Optional[str] = None,
    reply_markup: Dict[str, Any] | None = None,
    reply_to_message_id: Optional[int] = None,
):
    payload: Dict[str, Any] = {"chat_id": chat_id, "document": file_url_or_file_id}
    if caption is not None:
        payload["caption"] = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = _allowed_parse_mode(parse_mode)
    if pm: payload["parse_mode"] = pm
    if reply_markup: payload["reply_markup"] = reply_markup
    if reply_to_message_id is not None: payload["reply_to_message_id"] = reply_to_message_id
    return _api_post("sendDocument", payload)

def send_chat_action(chat_id: int | str, action: str = "typing"):
    """
    action: typing|upload_photo|record_video|upload_video|record_voice|upload_voice|
            upload_document|choose_sticker|find_location|record_video_note|upload_video_note
    """
    return _api_post("sendChatAction", {"chat_id": chat_id, "action": action})

def ask_for_location(chat_id: int | str, text: str):
    """
    ส่งข้อความพร้อมปุ่ม 'Share Location'
    """
    _log_debug("ASK_LOCATION", chat_id=chat_id)
    location_keyboard = {
        "keyboard": [[{"text": "📍 แชร์ตำแหน่งปัจจุบัน", "request_location": True}]],
        "one_time_keyboard": True,
        "resize_keyboard": True,
    }
    return send_message(
        chat_id,
        text=text,
        reply_markup=location_keyboard,
        parse_mode=None,
    )

def edit_message_text(
    chat_id: int | str,
    message_id: int,
    text: str,
    reply_markup: Dict[str, Any] | None = None,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
):
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": (text or "")[:TELEGRAM_MESSAGE_LIMIT],
        "disable_web_page_preview": disable_web_page_preview,
    }
    pm = _allowed_parse_mode(parse_mode)
    if pm: payload["parse_mode"] = pm
    if reply_markup: payload["reply_markup"] = reply_markup
    return _api_post("editMessageText", payload)

def answer_callback_query(callback_query_id: str, text: str | None = None, show_alert: bool = False):
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text: payload["text"] = text
    return _api_post("answerCallbackQuery", payload)

def set_webhook(url: str, drop_pending: bool = True, secret_token: Optional[str] = None):
    params: Dict[str, Any] = {
        "url": url,
        "allowed_updates": ["message", "edited_message", "callback_query"],
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
