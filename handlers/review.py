# handlers/review.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Optional
import re

from utils.message_utils import send_message, send_typing_action
from utils.review_utils import set_review, need_review_today

# ฟังก์ชันเสริม (มีหรือไม่มีไม่ทำให้พัง)
try:
    from utils.context_utils import update_context, is_waiting_review  # type: ignore
except Exception:  # pragma: no cover
    def update_context(*_a, **_kw):  # type: ignore
        return None
    def is_waiting_review(*_a, **_kw) -> bool:  # type: ignore
        return False

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_RATING_RE = re.compile(r"\b([1-5])\b")

def _extract_rating(text: str) -> Optional[int]:
    """
    ดึงคะแนน 1..5 ตัวแรกที่พบจากข้อความ เช่น:
    '/review 5', '/review ให้ 4 ดาว', 'รีวิว 3'
    """
    if not text:
        return None
    m = _RATING_RE.search(text)
    if not m:
        return None
    try:
        v = int(m.group(1))
        return v if 1 <= v <= 5 else None
    except Exception:
        return None

def _face_for(score: int) -> str:
    return {5: "🤩", 4: "😊", 3: "😐", 2: "🙁", 1: "😞"}.get(score, "⭐")

# ===== Main (มาตรฐานใหม่: รับ user_info, user_text) =====
def handle_review(user_info: Dict[str, Any], user_text: str) -> None:
    """
    ให้คะแนนบอทแบบง่าย ๆ
    - รองรับ: /review 1-5 หรือพิมพ์ข้อความที่มีเลข 1..5 ปนอยู่
    - ถ้าไม่ระบุคะแนน และระบบแจ้งว่าควรรีวิววันนี้ → ขอคะแนน
    - ถ้าไม่จำเป็นต้องรีวิว → แจ้งแนวทางสั้น ๆ
    """
    chat_id = user_info["profile"]["user_id"]
    user_id = str(user_info["profile"]["user_id"])
    user_name = user_info["profile"].get("first_name") or ""

    try:
        send_typing_action(chat_id, "typing")

        rating = _extract_rating(user_text or "")
        if rating is not None:
            # บันทึกคะแนน
            try:
                set_review(user_id, rating)
            except Exception as e:
                print(f"[handle_review] set_review error: {e}")
                send_message(chat_id, "❌ ขออภัยครับ เกิดปัญหาในการบันทึกคะแนน", parse_mode="HTML")
                return

            # อัปเดต context (ถ้ามี)
            try:
                update_context(user_id, {"waiting_review": False, "last_rating": rating})  # type: ignore
            except Exception:
                pass

            face = _face_for(rating)
            send_message(
                chat_id,
                f"✅ ขอบคุณสำหรับรีวิวครับคุณ {_html_escape(user_name)}! {face}\n"
                f"คะแนนที่ได้รับ: <b>{rating}/5</b>",
                parse_mode="HTML",
            )
            return

        # ยังไม่ได้ให้คะแนน → ดูว่าจำเป็นต้องรีวิววันนี้ไหม
        need_today = False
        try:
            need_today = bool(need_review_today(user_id))
        except Exception as e:
            print(f"[handle_review] need_review_today error: {e}")
            # ถ้าเช็คไม่ได้ ให้ถือว่าไม่จำเป็น แต่ยังบอกวิธีใช้
            need_today = False

        if need_today or is_waiting_review(user_id):  # type: ignore
            send_message(
                chat_id,
                "❓ กรุณารีวิวความพึงพอใจ (1–5): เช่น <code>/review 5</code>",
                parse_mode="HTML",
            )
        else:
            send_message(
                chat_id,
                "วันนี้ไม่จำเป็นต้องรีวิวครับ (แต่หากต้องการให้คะแนน พิมพ์ <code>/review 1-5</code> ได้เลย)",
                parse_mode="HTML",
            )

    except Exception as e:
        print(f"[handle_review] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในระบบรีวิว", parse_mode="HTML")

# ===== Legacy (รองรับโค้ดเก่าที่เรียกด้วย chat_id โดยตรง) =====
def handle_review_legacy(chat_id: int | str, user_text: str) -> None:
    """
    เวอร์ชันเข้ากันได้กับของเดิม: รับ (chat_id, user_text)
    """
    try:
        send_typing_action(chat_id, "typing")
        user_id = str(chat_id)

        rating = _extract_rating(user_text or "")
        if rating is not None:
            try:
                set_review(user_id, rating)
            except Exception as e:
                print(f"[handle_review_legacy] set_review error: {e}")
                send_message(chat_id, "❌ ขออภัยครับ เกิดปัญหาในการบันทึกคะแนน", parse_mode="HTML")
                return
            face = _face_for(rating)
            send_message(chat_id, f"✅ ขอบคุณสำหรับรีวิวครับ! {face}\nคะแนนที่ได้รับ: <b>{rating}/5</b>", parse_mode="HTML")
            return

        try:
            need_today = bool(need_review_today(user_id))
        except Exception:
            need_today = False

        if need_today:
            send_message(chat_id, "❓ กรุณารีวิวความพึงพอใจ (1–5): เช่น <code>/review 5</code>", parse_mode="HTML")
        else:
            send_message(chat_id, "วันนี้ไม่จำเป็นต้องรีวิวครับ (หรือให้คะแนนได้ด้วย <code>/review 1-5</code>)", parse_mode="HTML")
    except Exception as e:
        print(f"[handle_review_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในระบบรีวิว", parse_mode="HTML")
