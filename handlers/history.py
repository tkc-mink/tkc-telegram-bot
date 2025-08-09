# handlers/history.py
# -*- coding: utf-8 -*-

from utils.message_utils import send_message
from utils.history_utils import get_user_history


def handle_history(chat_id: int, user_text: str) -> None:
    """
    แสดงประวัติคำถาม/คำตอบของผู้ใช้คนนี้ล่าสุด 10 รายการ
    """
    try:
        user_id = str(chat_id)
        logs = get_user_history(user_id, limit=10) or []

        if not logs:
            send_message(chat_id, "🗒️ คุณยังไม่มีประวัติการใช้งานเลยครับ")
            return

        lines = []
        for item in logs:
            q = item.get("q", "")
            a = item.get("a", "")
            dt = item.get("date", "")
            lines.append(f"• [{dt}] {q}\n  └ {a}")

        text = "📜 <b>ประวัติย้อนหลัง (ล่าสุด 10 รายการ)</b>\n" + "\n".join(lines)
        send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        send_message(chat_id, f"❌ ไม่สามารถดึงประวัติได้: {e}")
