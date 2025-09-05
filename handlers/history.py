# handlers/history.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
from datetime import datetime

from utils.memory_store import get_user_chat_history
from utils.message_utils import send_message, send_typing_action

# ===== Config via ENV =====
_HISTORY_DEFAULT_LIMIT = int(os.getenv("HISTORY_DEFAULT_LIMIT", "10"))
_HISTORY_MAX_LIMIT     = int(os.getenv("HISTORY_MAX_LIMIT", "100"))
_HISTORY_SNIPPET_CHARS = int(os.getenv("HISTORY_SNIPPET_CHARS", "300"))  # ความยาวสูงสุดของแต่ละบรรทัด

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _parse_limit(user_text: str) -> int:
    """
    ดึงตัวเลขจากคำสั่ง เช่น '/my_history 20' → 20
    ถ้าไม่ระบุ → ใช้ค่าเริ่มต้น, และไม่เกิน _HISTORY_MAX_LIMIT
    """
    try:
        parts = (user_text or "").strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            n = int(parts[1])
            if n < 1:
                return _HISTORY_DEFAULT_LIMIT
            return min(n, _HISTORY_MAX_LIMIT)
    except Exception:
        pass
    return _HISTORY_DEFAULT_LIMIT

def _fmt_ts(ts_str: Optional[str]) -> str:
    """
    รับ ISO string แล้วคืน 'YYYY-MM-DD HH:MM'
    รองรับรูปแบบที่ลงท้ายด้วย 'Z' หรือมี timezone offset
    ถ้าแปลงไม่ได้ให้คืน '-'
    """
    if not ts_str:
        return "-"
    try:
        s = ts_str.strip()
        # รองรับรูปแบบลงท้าย Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        # ถ้ามี timezone ให้แปลงเป็น local ก่อน แล้วค่อย format
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        try:
            # fallback: ตัดช่วงนาทีต้น ๆ ที่พอดี
            return ts_str[:16]
        except Exception:
            return "-"

def _shorten(content: str, limit: int = _HISTORY_SNIPPET_CHARS) -> str:
    if not content:
        return ""
    if len(content) <= limit:
        return content
    return content[:limit - 1] + "…"

def _role_label(role: str) -> str:
    # แสดงเฉพาะ user/assistant ให้ชัดเจน
    if role == "user":
        return "คุณ"
    if role == "assistant":
        return "ผม"
    # อื่น ๆ (เช่น system/tool) แสดงชื่อดิบไว้ในวงเล็บ
    return f"{_html_escape(role)}"

def _format_history_lines(items: List[Dict[str, Any]]) -> str:
    """
    แปลงรายการประวัติให้เป็นข้อความ HTML:
    • <code>YYYY-MM-DD HH:MM</code> <b>คุณ/ผม</b>: เนื้อหา…
    (escape ทุกจุดกันฟอร์แมตพัง)
    """
    lines: List[str] = []
    for it in items:
        ts = _fmt_ts(it.get("timestamp"))
        role = _role_label(str(it.get("role", "")))
        content = _shorten(str(it.get("content", "") or ""))
        # escape content; role อาจไม่มีการ escape ในกรณี user/assistant (เป็นไทยล้วนแล้วปลอดภัย)
        lines.append(f"• <code>{_html_escape(ts)}</code> <b>{role}</b>: {_html_escape(content)}")
    return "\n".join(lines)

# ===== Main Handler =====
def handle_history(user_info: Dict[str, Any], user_text: str) -> None:
    """
    แสดงประวัติการสนทนา N รายการล่าสุด (ค่าเริ่มต้น 10; ระบุได้ เช่น '/my_history 20')
    - จัดเรียงเก่าสุด → ใหม่สุด ภายในช่วงที่เลือก (อ่านไหลลื่น)
    - ปลอดภัยต่อ HTML และแบ่งข้อความอัตโนมัติผ่าน utils.message_utils
    """
    chat_id = user_info["profile"]["user_id"]

    try:
        send_typing_action(chat_id, "typing")

        # 1) อ่านประวัติทั้งหมด
        full_history = get_user_chat_history(chat_id) or []
        if not full_history:
            send_message(chat_id, "ยังไม่มีประวัติการสนทนาครับ", parse_mode="HTML")
            return

        # 2) เลือกจำนวนที่จะแสดง
        limit = _parse_limit(user_text)
        # เลือกช่วงท้ายสุด 'limit' รายการ แล้วเรียงจากเก่า → ใหม่
        tail = full_history[-limit:]
        # บางระบบเก็บล่าสุดไว้ท้ายอยู่แล้ว; ตรงนี้ถือว่าคงลำดับเดิม tail เป็นเก่า→ใหม่
        # หากระบบของคุณเก็บล่าสุดไว้ 'หัว' ให้สลับ: tail = list(reversed(full_history))[:limit][::-1]

        # 3) ฟอร์แมตข้อความ
        header = f"🗂️ <b>ประวัติการสนทนา {len(tail)} รายการล่าสุด</b>\n"
        body = _format_history_lines(tail)
        footer = (
            "\n\nเคล็ดลับ: ระบุจำนวนที่ต้องการดูได้ เช่น "
            "<code>/my_history 20</code> (สูงสุด "
            f"{_HISTORY_MAX_LIMIT})"
        )
        msg = header + body + footer

        # 4) ส่ง (wrapper จะจัดการแบ่ง 4096 อัตโนมัติ)
        send_message(chat_id, msg, parse_mode="HTML")

    except Exception as e:
        print(f"[handle_history] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงประวัติการสนทนา", parse_mode="HTML")
