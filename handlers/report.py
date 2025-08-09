# handlers/report.py
# -*- coding: utf-8 -*-

from utils.report_utils import get_daily_report, get_weekly_report
from utils.message_utils import send_message


def handle_report(chat_id: int, user_text: str) -> None:
    """
    /report หรือ /summary
    - ถ้ามีคำว่า week/สัปดาห์ => รายสัปดาห์
    - ไม่งั้น => รายวัน
    """
    try:
        text = (user_text or "").strip().lower()
        if "week" in text or "สัปดาห์" in text:
            msg = get_weekly_report()
        else:
            msg = get_daily_report()
        send_message(chat_id, msg, parse_mode="HTML")
    except Exception as e:
        send_message(chat_id, f"❌ สร้างรายงานไม่สำเร็จ: {e}")
