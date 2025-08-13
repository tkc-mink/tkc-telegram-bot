# handlers/lottery.py
# -*- coding: utf-8 -*-
"""
Handler for fetching the latest lottery results, upgraded to use the new
user profile system and a reliable, keyless utility.
"""
from __future__ import annotations
from typing import Dict, Any

# --- ✅ ส่วนที่เราแก้ไข ---
# 1. เปลี่ยนไป import ฟังก์ชันใหม่จาก utils และ telegram_api ที่เราใช้เป็นมาตรฐาน
from utils.lottery_utils import get_lottery_result
from utils.telegram_api import send_message

def handle_lottery(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Fetches the latest lottery results using the new utility and sends them to the user.
    Note: The new utility does not support querying by date to ensure reliability.
    """
    # 2. ดึงข้อมูลที่จำเป็นจาก user_info ที่ได้รับมา
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']

    print(f"[handle_lottery] Received lottery request from user {user_name} (ID: {chat_id})")

    try:
        # 3. แจ้งให้ผู้ใช้ทราบว่ากำลังทำงาน
        send_message(chat_id, "🔎 กำลังตรวจสอบผลสลากกินแบ่งรัฐบาลล่าสุดสักครู่นะครับ...")

        # 4. เรียกใช้ get_lottery_result จาก lottery_utils เวอร์ชันใหม่ของเรา
        # เวอร์ชันใหม่นี้จะดึงงวดล่าสุดเสมอเพื่อความแม่นยำ
        lottery_message = get_lottery_result()

        # 5. ส่งผลลัพธ์ที่ได้กลับไป
        send_message(chat_id, lottery_message, parse_mode="Markdown")

    except Exception as e:
        # 6. ปรับปรุงการจัดการ Error ให้เป็นมิตรมากขึ้น
        print(f"[handle_lottery] An unhandled error occurred: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดในการดึงผลสลากครับ")
