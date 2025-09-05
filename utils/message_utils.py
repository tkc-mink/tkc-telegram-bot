# utils/message_utils.py
# -*- coding: utf-8 -*-
"""
Thin wrapper ที่เข้ากับโค้ดเดิม แต่ใต้ท้องใช้ utils.telegram_api

สิ่งที่ทำ:
- รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN (ยึด config.py เป็นหลัก)
- ฟังก์ชัน get_telegram_token() แบบ public เพื่อความเข้ากันได้กับโค้ดเดิม
- รองรับ parse_mode ("HTML" / "Markdown" / "MarkdownV2") อย่างถูกต้อง
- ✅ บล็อคข้อความแนว "รับทราบ:/คุณถามว่า:/สรุปคำถาม:" ก่อนส่ง (กันบอททวนคำถาม)
- ✅ ไม่ตัดข้อความทิ้ง: จะแบ่งข้อความเป็นก้อนละ ≤4096 ตัวอักษรอัตโนมัติ
- ✅ ส่งสถานะกำลังพิมพ์ (send_typing_action) + ออปชัน auto_typing
- ✅ retry ฉลาดขึ้น (จับ retry_after จาก Telegram + backoff + jitter)
- ✅ ออปชันเสริม: disable_notification / protect_content / reply_to_message_id

หมายเหตุ:
- ดีฟอลต์ parse_mode = "HTML" เพื่อความเสถียร
- ถ้าใช้ MarkdownV2 และข้อความยังไม่ escape เอง อาจเกิด formatting error ได้
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import os
import json
import re
import time
import random

# ===== Read token from config first (standard) =====
try:
    from config import TELEGRAM_BOT_TOKEN as _CFG_BOT_TOKEN  # type: ignore
except Exception:
    _CFG_BOT_TOKEN = ""

# ===== Low-level Telegram API helpers (มี debug ภายใน) =====
from utils.telegram_api import (
    _api_post,                        # ใช้เป็นหลักเพื่อควบคุม retry/response
)

ALLOWED_PARSE = {"HTML", "MARKDOWN", "MARKDOWNV2"}  # จะ upper() ก่อนเช็ค
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_CAPTION_LIMIT = 1024


# ===== Token helpers =====
def get_telegram_token() -> str:
    """
    คืนค่า Telegram Bot Token (ยึด config เป็นหลัก แล้วค่อย fallback ไป ENV เก่า)
    - มีไว้ให้โมดูลอื่น import ได้ (ความเข้ากันได้กับโค้ดเดิม)
    """
    tok = (
        (_CFG_BOT_TOKEN or "").strip()
        or (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        or (os.getenv("TELEGRAM_TOKEN") or "").strip()
    )
    if not tok:
        print("[message_utils] WARNING: Telegram token not set (config/ENV)")
    return tok


def _log(tag: str, **kw):
    try:
        print(f"[message_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[message_utils] {tag} :: (unprintable log)")


def _safe_preview(s: str, n: int = 160) -> str:
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
    if text is None:
        return [""]
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return [""]

    parts: List[str] = []
    buf: List[str] = []
    cur_len = 0

    lines = text.splitlines(True)  # เก็บ \n ไว้
    for ln in lines:
        L = len(ln)
        if cur_len + L <= limit:
            buf.append(ln); cur_len += L
            continue

        if L > limit:
            # บรรทัดยาวเกิน limit เอง → ตัดเป็นท่อน ๆ
            if buf:
                parts.append("".join(buf)); buf, cur_len = [], 0
            chunk = ln
            while len(chunk) > limit:
                parts.append(chunk[:limit])
                chunk = chunk[limit:]
            if chunk:
                buf.append(chunk); cur_len = len(chunk)
        else:
            # ปิดก้อนเดิม แล้วเริ่มใหม่
            parts.append("".join(buf))
            buf = [ln]; cur_len = L

    if buf:
        parts.append("".join(buf))

    # อีกรอบ: ถ้าบางชิ้นยังยาวเกิน (กรณีไม่มี \n เลย) ให้ตัดด้วยช่องว่าง
    normalized: List[str] = []
    for p in parts:
        if len(p) <= limit:
            normalized.append(p); continue
        words = p.split(" ")
        cur, l = [], 0
        for w in words:
            add = (w + " ")
            if l + len(add) > limit and cur:
                normalized.append("".join(cur).rstrip())
                cur, l = [], 0
            cur.append(add); l += len(add)
        if cur:
            normalized.append("".join(cur).rstrip())

    return normalized or [""]


# ===== Retry helpers (จับ retry_after + backoff + jitter) =====
def _extract_retry_after(err: Any) -> Optional[int]:
    """
    พยายามดึงค่า retry_after จาก error (ทั้งแบบ dict ของ Telegram และจากข้อความ)
    โครงสร้างมาตรฐานของ Telegram กรณี rate limit:
    {"ok": false, "error_code": 429, "description": "...", "parameters": {"retry_after": N}}
    """
    # แบบ dict
    try:
        if isinstance(err, dict):
            params = err.get("parameters") or {}
            if isinstance(params, dict) and "retry_after" in params:
                return int(params["retry_after"])
            # บางไลบรารีคืน description แบบข้อความ "Too Many Requests: retry after X"
            desc = err.get("description") or ""
            m = re.search(r"retry after (\d+)", str(desc), flags=re.IGNORECASE)
            if m:
                return int(m.group(1))
    except Exception:
        pass

    # แบบ Exception / ข้อความ
    try:
        s = str(err)
        m = re.search(r"retry after (\d+)", s, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _send_with_retry(method: str, payload: Dict[str, Any], max_attempts: int = 3) -> Optional[Dict[str, Any]]:
    """
    เรียก Telegram API (ผ่าน _api_post) พร้อม retry ฉลาด:
    - ถ้าเจอ 429 และเจอ retry_after จะรออัตโนมัติ (เพิ่ม jitter)
    - อื่น ๆ จะ backoff เล็กน้อย 0.4s, 0.8s, ...
    """
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            resp = _api_post(method, payload)
            # บางกรณี _api_post อาจคืน dict ที่มี ok=false ให้เราจัดการเอง
            if isinstance(resp, dict) and resp.get("ok") is False:
                ra = _extract_retry_after(resp)
                if ra:
                    wait_s = ra + random.uniform(0.05, 0.35)
                    _log("RATE_LIMIT", method=method, retry_after=ra, wait=round(wait_s, 3), attempt=attempt)
                    time.sleep(wait_s)
                    continue
                # ไม่ใช่ rate limit → ถือเป็น error ทั่วไป
                _log("TELEGRAM_ERROR", method=method, resp=_safe_preview(json.dumps(resp, ensure_ascii=False), 300))
                if attempt < max_attempts:
                    time.sleep(0.3 * attempt)
                    continue
                return None
            return resp
        except Exception as e:
            ra = _extract_retry_after(e)
            if ra:
                wait_s = ra + random.uniform(0.05, 0.35)
                _log("RATE_LIMIT_EX", method=method, retry_after=ra, wait=round(wait_s, 3), attempt=attempt)
                time.sleep(wait_s)
                continue
            _log("WARN_RETRY", method=method, attempt=attempt, err=str(e))
            if attempt < max_attempts:
                time.sleep(0.4 * attempt)
                continue
            _log("ERROR_AFTER_RETRY", method=method, err=str(e))
            return None
    return None


# ===== Chat actions =====
def send_typing_action(chat_id: int | str, action: str = "typing") -> None:
    """
    ส่งสถานะกำลังพิมพ์/อัปโหลด ฯลฯ
    action: typing|upload_photo|record_video|upload_video|record_voice|upload_voice|
            upload_document|choose_sticker|find_location|record_video_note|upload_video_note
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, action="send_typing_action")
        return
    try:
        _send_with_retry("sendChatAction", {"chat_id": chat_id, "action": action}, max_attempts=3)
    except Exception as e:
        _log("ERROR_CHAT_ACTION", err=str(e))


def _normalize_parse_mode(parse_mode: Optional[str]) -> str:
    """
    คืนค่า parse_mode ที่ปลอดภัย (HTML เป็นค่าเริ่มต้น)
    """
    pm = (parse_mode or "HTML").strip()
    pm_up = pm.upper()
    if pm_up not in ALLOWED_PARSE:
        return "HTML"
    # คืนรูปแบบต้นทาง (เคสถูกต้อง) ให้สวยงาม
    return "MarkdownV2" if pm_up == "MARKDOWNV2" else ("Markdown" if pm_up == "MARKDOWN" else "HTML")


# ===== High-level senders =====
def send_message(
    chat_id: int | str,
    text: str,
    parse_mode: Optional[str] = None,
    disable_preview: bool = True,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
    auto_typing: bool = True,
    *,
    disable_notification: bool = False,
    protect_content: bool = False,
) -> None:
    """
    ส่งข้อความไป Telegram
    - แบ่งข้อความยาวเป็นก้อนละ ≤4096 ตัวอักษร (ไม่ตัดทิ้ง)
    - ✅ บล็อคข้อความแนวทวน/ยืนยันก่อนส่ง (เฉพาะชิ้นแรกเท่านั้น)
    - รองรับ parse_mode (HTML/Markdown/MarkdownV2)
    - ส่งสถานะกำลังพิมพ์อัตโนมัติเมื่อ auto_typing=True
    - ออปชันเสริม: disable_notification / protect_content (เฉพาะชิ้นแรก)
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, text_preview=_safe_preview(text))
        return

    pm = _normalize_parse_mode(parse_mode)
    chunks = _split_for_telegram(text or "")
    if not chunks:
        chunks = [""]

    # block เฉพาะชิ้นแรก (เลี่ยงบล็อคคำตอบจริงที่แบ่งหลายชิ้น)
    if _should_block_no_echo(chunks[0]):
        _log("BLOCK_NO_ECHO", chat_id=chat_id, blocked_preview=_safe_preview(chunks[0]))
        return

    try:
        for idx, chunk in enumerate(chunks):
            if auto_typing:
                # ส่ง typing action ก่อนยิงข้อความแต่ละชิ้น
                send_typing_action(chat_id, action="typing")

            payload: Dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": pm,
                "disable_web_page_preview": disable_preview,
            }
            # ใส่ reply_markup / reply_to_message_id / disable_notification / protect_content เฉพาะชิ้นแรกพอ
            if idx == 0:
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                if reply_to_message_id is not None:
                    payload["reply_to_message_id"] = reply_to_message_id
                if disable_notification:
                    payload["disable_notification"] = True
                if protect_content:
                    payload["protect_content"] = True

            _send_with_retry("sendMessage", payload, max_attempts=3)
    except Exception as e:
        _log("ERROR_SEND_MESSAGE", err=str(e))


def send_photo(
    chat_id: int | str,
    photo_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
    auto_typing: bool = True,
    *,
    disable_notification: bool = False,
    protect_content: bool = False,
) -> None:
    """
    ส่งรูปภาพไป Telegram (ด้วย URL หรือ file_id)
    - จำกัด caption ~1024 ตัวอักษรตามข้อกำหนด Telegram
    - รองรับ parse_mode (MarkdownV2/Markdown/HTML)
    - auto_typing จะส่ง action=upload_photo ก่อน
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, photo=_safe_preview(photo_url))
        return

    cap = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = _normalize_parse_mode(parse_mode)

    try:
        if auto_typing:
            send_typing_action(chat_id, action="upload_photo")

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": cap,
            "parse_mode": pm,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if disable_notification:
            payload["disable_notification"] = True
        if protect_content:
            payload["protect_content"] = True

        _send_with_retry("sendPhoto", payload, max_attempts=3)
    except Exception as e:
        _log("ERROR_SEND_PHOTO", err=str(e))


def send_document(
    chat_id: int | str,
    file_url: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = None,
    reply_markup: Optional[Dict[str, Any]] = None,
    reply_to_message_id: Optional[int] = None,
    auto_typing: bool = True,
    *,
    disable_notification: bool = False,
    protect_content: bool = False,
) -> None:
    """
    ส่งเอกสาร/ไฟล์ (โดยให้เป็น URL หรือ file_id)
    - รองรับ parse_mode
    - auto_typing จะส่ง action=upload_document ก่อน
    """
    token = get_telegram_token()
    if not token:
        _log("WARN_NO_TOKEN", chat_id=chat_id, document=_safe_preview(file_url))
        return

    cap = (caption or "")[:TELEGRAM_CAPTION_LIMIT]
    pm = _normalize_parse_mode(parse_mode)

    try:
        if auto_typing:
            send_typing_action(chat_id, action="upload_document")

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "document": file_url,
            "caption": cap,
            "parse_mode": pm,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if disable_notification:
            payload["disable_notification"] = True
        if protect_content:
            payload["protect_content"] = True

        _send_with_retry("sendDocument", payload, max_attempts=3)
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
        _send_with_retry("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
            "parse_mode": "HTML",
        }, max_attempts=3)
    except Exception as e:
        _log("ERROR_ASK_LOCATION", err=str(e))
