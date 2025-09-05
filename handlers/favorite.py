# handlers/favorite.py
# -*- coding: utf-8 -*-
"""
Handler for user favorites, fully integrated with the persistent database.
Single entry handles: /favorite_add, /favorite_list, /favorite_remove
Stable + safe: HTML escaping, retry/auto-chunk via utils.message_utils.
"""
from __future__ import annotations
from typing import Dict, Any, List
import os
import re

from utils.message_utils import send_message, send_typing_action
from utils.favorite_utils import add_new_favorite, get_user_favorites, remove_user_favorite

# ===== Config (via ENV) =====
_FAVORITE_MAX_CHARS  = int(os.getenv("FAVORITE_MAX_CHARS", "2000"))   # ความยาวสูงสุดที่ “เก็บ”
_FAVORITE_LIST_LIMIT = int(os.getenv("FAVORITE_LIST_LIMIT", "10"))     # จำนวนรายการที่แสดง/ใช้อ้างอิง index

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _truncate(s: str, max_len: int = 300) -> str:
    s = s or ""
    return (s[: max_len - 1] + "…") if len(s) > max_len else s

def _normalize_content(s: str) -> str:
    """ลดช่องว่างซ้ำ/แถวว่างต่อกัน เคลียร์ zero-width ให้อ่านง่ายและเก็บสั้นลง"""
    if not s:
        return ""
    s = s.replace("\x00", "")
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)       # zero-width
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # ตัดแถวหน้า/ท้าย + บีบช่องว่างยาว
    lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in s.split("\n")]
    # ลบแถวว่างติด ๆ กันให้เหลือไม่เกิน 1
    cleaned: List[str] = []
    for ln in lines:
        if ln == "" and (cleaned and cleaned[-1] == ""):
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned).strip()
    # จำกัดความยาวที่ “เก็บ”
    return out[:_FAVORITE_MAX_CHARS]

def _usage_text() -> str:
    return (
        "<b>คำสั่งสำหรับจัดการรายการโปรด</b>\n"
        f"• <code>/favorite_add &lt;ข้อความ&gt;</code>  (เก็บสูงสุด {_FAVORITE_MAX_CHARS} ตัวอักษร)\n"
        f"• <code>/favorite_list</code>  (แสดง {_FAVORITE_LIST_LIMIT} รายการล่าสุด)\n"
        "• <code>/favorite_remove &lt;ลำดับ&gt;</code>"
    )

def _format_favorites_list(favs: List[Dict]) -> str:
    """Formats the list of favorites beautifully and safely (HTML)."""
    if not favs:
        return "📭 คุณยังไม่มีรายการโปรดเลยครับ"

    lines = [f"⭐ <b>รายการโปรด {_FAVORITE_LIST_LIMIT} อันดับล่าสุดของคุณ</b>"]
    for i, item in enumerate(favs, start=1):
        try:
            raw = str(item.get("content", ""))
        except Exception:
            raw = ""
        content = _truncate(_html_escape(raw).strip(), 800)
        if not content:
            content = "-"
        lines.append(f"{i}. <b>{content}</b>")
    lines.append("\nลบรายการ: <code>/favorite_remove &lt;ลำดับ&gt;</code>")
    return "\n".join(lines)

def _parse_index(idx_text: str) -> int | None:
    """รับเฉพาะเลขจำนวนเต็มบวก (1..N) เท่านั้น"""
    if not (idx_text and idx_text.isdigit()):
        return None
    idx = int(idx_text)
    return idx if idx >= 1 else None

# ===== Main Handler =====
def handle_favorite(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Handles all favorite sub-commands:
      - /favorite_add <content>
      - /favorite_list
      - /favorite_remove <index>
    """
    user_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        text = (user_text or "").strip()
        if not text:
            send_message(user_id, _usage_text(), parse_mode="HTML")
            return

        parts = text.split()
        command = parts[0].lower()

        # --- /favorite_add <content> ---
        if command == "/favorite_add":
            # ตัดคำสั่งออก แล้ว normalize
            content_to_add = text[len(command):].strip()
            if not content_to_add:
                send_message(
                    user_id,
                    "วิธีใช้: <code>/favorite_add &lt;ข้อความที่ต้องการบันทึก&gt;</code>",
                    parse_mode="HTML",
                )
                return
            send_typing_action(user_id, "typing")

            content_to_store = _normalize_content(content_to_add)
            if not content_to_store:
                send_message(user_id, "ข้อความว่างหรือไม่เหมาะสมสำหรับการบันทึกครับ", parse_mode="HTML")
                return

            ok = False
            try:
                ok = add_new_favorite(user_id, content_to_store)
            except Exception as e:
                print(f"[handle_favorite] add error: {e}")
                ok = False

            if ok:
                # แสดงตัวอย่างบางส่วนที่บันทึกจริง (escape แล้ว)
                preview = _truncate(_html_escape(content_to_s_
