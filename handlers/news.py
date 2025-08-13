# handlers/news.py
# -*- coding: utf-8 -*-
"""
Handler for fetching and displaying the latest news,
upgraded to use the new user profile system and reliable news utility.
"""
from __future__ import annotations
from typing import Dict, Any

# --- ✅ ส่วนที่เราแก้ไข ---
# 1. เปลี่ยนไป import ฟังก์ชันใหม่จาก utils และ telegram_api ที่เราใช้เป็นมาตรฐาน
from utils.news_utils import get_news
from utils.telegram_api import send_message

def handle_news(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Parses the news topic from user text, fetches news using the new utility, and sends it.
    Example uses:
    - /news
    - /news เศรษฐกิจไทย
    """
    # 2. ดึงข้อมูลที่จำเป็นจาก user_info ที่ได้รับมา
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']

    print(f"[handle_news] Received news request from user {user_name} (ID: {chat_id})")

    try:
        # 3. เพิ่มความฉลาดในการหา "หัวข้อข่าว" จากข้อความของผู้ใช้
        parts = user_text.split(maxsplit=1)
        topic = "ข่าวล่าสุด" # ค่าเริ่มต้นถ้าผู้ใช้พิมพ์แค่ /news
        if len(parts) > 1 and parts[1].strip():
            topic = parts[1].strip()
        
        # 4. แจ้งให้ผู้ใช้ทราบว่ากำลังทำงาน
        send_message(chat_id, f"🔎 กำลังค้นหาข่าวในหัวข้อ '{topic}' สักครู่นะครับ...")

        # 5. เรียกใช้ get_news จาก news_utils เวอร์ชันใหม่ของเรา
        news_message = get_news(topic)

        # 6. ส่งผลลัพธ์ที่ได้กลับไป (รองรับ Markdown สำหรับลิงก์)
        send_message(chat_id, news_message, parse_mode="Markdown")

    except Exception as e:
        # 7. ปรับปรุงการจัดการ Error ให้เป็นมิตรมากขึ้น
        print(f"[handle_news] An unhandled error occurred: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดในการค้นหาข่าวครับ")
