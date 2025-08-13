# handlers/report.py
# -*- coding: utf-8 -*-
"""
Handler for generating system reports, using the new report_utils.
"""
from __future__ import annotations
from typing import Dict, Any

from utils.telegram_api import send_message
from utils.report_utils import get_system_report # ✅ ใช้เครื่องมือใหม่

def handle_report(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Handles the /report command by generating and sending a system-wide usage report.
    (Note: daily/weekly logic is simplified to one comprehensive report for now)
    """
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    
    print(f"[handle_report] Request from user {user_name} (ID: {chat_id})")

    try:
        # แจ้งให้ผู้ใช้ทราบว่ากำลังทำงาน
        send_message(chat_id, "🔎 กำลังรวบรวมข้อมูลเพื่อสร้างรายงานสักครู่นะครับ...")
        
        # เรียกใช้ฟังก์ชันสร้างรายงานใหม่
        report_message = get_system_report()

        # ส่งรายงานกลับไป
        send_message(chat_id, report_message, parse_mode="Markdown")

    except Exception as e:
        print(f"[handle_report] An unhandled error occurred: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดในการสร้างรายงานครับ")
