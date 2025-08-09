# handlers/lottery.py
# -*- coding: utf-8 -*-

from utils.message_utils import send_message
from utils.serp_utils import get_lottery_result


def handle_lottery(chat_id: int, user_text: str) -> None:
    """
    ใช้:
    - /lottery                     -> ผลล่าสุด
    - /lottery 1 กรกฎาคม 2567     -> ระบุวันที่ (ถ้าระบบรองรับ)
    """
    try:
        parts = (user_text or "").strip().split(" ", 1)
        query_date = parts[1].strip() if len(parts) == 2 else None

        result_html = get_lottery_result(query_date)  # คืน HTML พร้อมจัดรูปแบบ
        send_message(chat_id, result_html, parse_mode="HTML")
    except Exception as e:
        send_message(chat_id, f"❌ ไม่สามารถดึงผลสลากได้: {e}")
