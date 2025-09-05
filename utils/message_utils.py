# utils/message_utils.py
# -*- coding: utf-8 -*-
"""
Thin wrapper ที่เข้ากับโค้ดเดิม แต่ใต้ท้องใช้ utils.telegram_api

สิ่งที่ทำ:
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
- ฟังก์ชัน get_telegram_token() แบบ public เพื่อความเข้ากันได้กับโค้ดเดิม
- รองรับ parse_mode ("HTML" / "Markdown" / "MarkdownV2") อย่างถูกต้อง
- ✅ บล็อคข้อความแนว "รับทราบ:/คุณถามว่า:/สรุปคำถาม:" ก่อนส่ง (กันบอททวนคำถาม)
- ✅ ไม่ตัดข้อความทิ้ง: จะแบ่งข้อความเป็นก้อนละ ≤4096 ตัวอักษรอัตโนมัติ
- ✅ ส่งสถานะกำลังพิมพ์ (send_typing_action)
- ✅ มี retry เบา ๆ 1 ครั้งกรณีล้มเหลวชั่วคราว
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import os
import json
import re
import time
import random

# ฟังก์ชันระดับล่างจาก telegram_api (มี log ดีบักให้แล้ว)
from utils.telegram_api import (
    send_message as tg_send_message,
    send_photo as tg_send_photo,
)
from utils.telegram_api import _api_post  # ใช้เมื่อจำเป็นต้องระบุพารามิเตอร์เอง

ALLOWED_PARSE = {"HTML", "Markdown", "MarkdownV2"}
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024

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
    try:
        print(f"[message_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[message_utils] {tag} :: (unprintable log)")

def _safe_preview(s: str, n: int = 120) -> str:
    s = s or ""
    return (s[:n] + "…") if len(s) > n else s

# ===== No-echo blocker (กันข้อความทวน/ยืนยันคำถาม) =====
_NO_ECHO_PREFIXES = re.compile(
    "|".join([
        r"^\s*รับทราบ(?:ครับ|ค่ะ|นะ)?[:：-]\s*",
        r"^\s*คุณ\s*ถามว่า[:：-]\s*",
        r"^\s*สรุปคำถาม[:：-]\s*",
        r"^\s*ยืนยันคำถาม[:：-]\s*",
        r"^\s*คำถามของคุณ[:：-]\s*",
        r"^\s*Question[:：-]\s*",
        r"^\s*You\s+asked[:：-]\s*",
    ]),
    re.IGNORECASE | re.UNICODE,
)

def _should_block_no_echo(text: str) -> bool:
    """
    บล็อคข้อความที่ขึ้นต้นด้วย pattern การทวน/ยืนยันคำถาม
    - กัน false positive โดยบล็อคเฉพาะข้อความที่ไม่มีบรรทัดใหม่ (ส่วนใหญ่เป็น ack สั้น ๆ)
    """
    if not text:
        return False
    if "\n" in text:  # ข้อความหลายบรรทัดมักเป็นคำตอบจริง
        return False
    return bool(_NO_ECHO_PREFIXES.match(text))

# ===== Split helper =====
def _split_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> List[str]:
    """
    แบ่งข้อความเป็นหลายชิ้นให้ไม่เกิน limit (4096) โดยพยายามตัดตามบรรทัด/ช่องว่าง
    """
    if not text:
        return [""]

    parts: List[str] = []
    buf: List[str] = []
    cur_len = 0

    lines = text.splitlines(True)  # เก็บ \n ไว้
    for ln in lines:
        L = len(ln)
        if cur_len + L <= limit:
            buf.append(ln)
            cur_len += L
            continue

        if L > limit:
            # บรรทัดยาวเกิน limit เอง → ตัดเป็นท่อน ๆ
            if buf:
                parts.append("".join(buf))
                buf, cur_len = [], 0
            chunk = ln
            while len(chunk) > limit:
                parts.append(chunk[:limit])
                chunk = chunk[limit:]
            if chunk:
                buf.append(chunk)
                cur_len = len(chunk)
        else:
            # ปิดก้อนเดิม แล้วเริ่มใหม่
            parts.append("".join(buf))
            buf = [ln]
            cur_len = L

    if buf:
        parts.append("".join(buf))

    # อีกรอบ: ถ้าบางชิ้นยังยาวเกิน (กรณีไม่มี \n เลย) ให้ตัดด้วยช่องว่าง
    normalized: List[str] = []
    for p in parts:
        if len(p) <= limit:
            normalized.append(p)
            continue
        # split by words
        words = p.split(" ")
        cur, l = [], 0
        for w in words:
            add = (w + " ")
            if l + len(add) > limit and cur:
                normalized.append("".join(cur).rstrip())
                cur, l = [], 0
            cur.append(add)
            l += len(add)
        if cur:
            normalized.append("".join(cur).rstrip())

    return normalized or [""]

# ===== Retry helper =====
def _with_retry(func, *args, **kwargs):
    """
    retry เบา ๆ 1 ครั้ง (หน่วงสุ่มเล็กน้อย) กรณี error ชั่วคราว
    """
    try:
        return func(*args, **kwargs)
    except Exception as e1:
        _log("WARN_RETRY_ONCE", err=str(e1))
        time.sleep(0.3 + random.random() * 0.5)
        try:
            return func(*args, **kwargs)
        except Exception as e2:
            _log("ERROR_AFTER_RETRY", err=str(e2))
            return None

# ===== High-level senders =====
def send_typing_action(chat_id: int | str, action: str = "typing") -> None:
    """
    ส่งสถานะกำลังพิมพ์/อัปโหลด ฯลฯ
    action: typing|upload_photo|record_video|upload_video|record_voice|upload_voice|upload_document|choose_sticker|find_location|record_video_note|upload_video_note
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, action="send_typing_action")
        return
    try:
        _with_retry(_api_post, "sendChatAction", {"chat_id": chat_id, "action": action})
    except Exception as e:
        _log("ERROR_CHAT_ACTION", err=str(e))

def send_message(
    chat_id: int | str,
    text: str,
    parse_mode: Optional[str] = None,
    disable_preview: bool = True,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """
    ส่งข้อความไป Telegram
    - แบ่งข้อความยาวเป็นก้อนละ ≤4096 ตัวอักษร (ไม่ตัดทิ้ง)
    - ถ้า parse_mode != "HTML" จะใช้ _api_post เพื่อระบุ parse_mode ตรง ๆ
    - ✅ บล็อคข้อความแนวทวน/ยืนยันก่อนส่ง (เฉพาะชิ้นแรกเท่านั้น)
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, text_preview=_safe_preview(text))
        return

    pm = (parse_mode or "HTML")
    if pm not in ALLOWED_PARSE:
        pm = "HTML"

    chunks = _split_for_telegram(text or "")
    if not chunks:
        chunks = [""]

    # block เฉพาะชิ้นแรก (เลี่ยงบล็อคคำตอบจริงที่แบ่งหลายชิ้น)
    if _should_block_no_echo(chunks[0]):
        _log("BLOCK_NO_ECHO", chat_id=chat_id, blocked_preview=_safe_preview(chunks[0]))
        return

    try:
        for idx, chunk in enumerate(chunks):
            if pm != "HTML":
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": pm,
                    "disable_web_page_preview": disable_preview,
                }
                if reply_markup and idx == 0:
                    payload["reply_markup"] = reply_markup
                if reply_to_message_id and idx == 0:
                    payload["reply_to_message_id"] = reply_to_message_id
                _with_retry(_api_post, "sendMessage", payload)
            else:
                # ใช้ helper ปกติ (default = HTML ใน telegram_api)
                # ใส่ reply_markup / reply_to_message_id เฉพาะชิ้นแรกพอ
                if idx == 0 and (reply_markup or reply_to_message_id is not None):
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": disable_preview,
                    }
                    if reply_markup:
                        payload["reply_markup"] = reply_markup
                    if reply_to_message_id is not None:
                        payload["reply_to_message_id"] = reply_to_message_id
                    _with_retry(_api_post, "sendMessage", payload)
                else:
                    _with_retry(tg_send_message, chat_id, chunk, reply_markup=None)
    except Exception as e:
        _log("ERROR_SEND_MESSAGE", err=str(e))

def send_photo(
    chat_id: int | str,
    photo_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """
    ส่งรูปภาพไป Telegram
    - จำกัด caption ~1024 ตัวอักษรตามข้อกำหนด Telegram
    - รองรับ parse_mode ถ้าต้องการ (MarkdownV2/Markdown/HTML)
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, photo=_safe_preview(photo_url))
        return

    cap = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = (parse_mode or "HTML")
    if pm not in ALLOWED_PARSE:
        pm = "HTML"

    try:
        if pm == "HTML" and not reply_markup and reply_to_message_id is None:
            _with_retry(tg_send_photo, chat_id, photo_url, caption=cap)
        else:
            payload = {
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": cap,
                "parse_mode": pm,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            if reply_to_message_id is not None:
                payload["reply_to_message_id"] = reply_to_message_id
            _with_retry(_api_post, "sendPhoto", payload)
    except Exception as e:
        _log("ERROR_SEND_PHOTO", err=str(e))

def send_document(
    chat_id: int | str,
    file_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
) -> None:
    """
    ส่งเอกสาร/ไฟล์ (โดยให้เป็น URL) — เผื่อใช้งาน
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, document=_safe_preview(file_url))
        return

    cap = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = (parse_mode or "HTML")
    if pm not in ALLOWED_PARSE:
        pm = "HTML"

    try:
        payload = {
            "chat_id": chat_id,
            "document": file_url,
            "caption": cap,
            "parse_mode": pm,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        _with_retry(_api_post, "sendDocument", payload)
    except Exception as e:
        _log("ERROR_SEND_DOCUMENT", err=str(e))

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
        _with_retry(_api_post, "sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
            "parse_mode": "HTML",
        })
    except Exception as e:
        _log("ERROR_ASK_LOCATION", err=str(e))
