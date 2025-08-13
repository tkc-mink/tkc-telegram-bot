# handlers/weather.py
# -*- coding: utf-8 -*-
"""
Handler for fetching weather, now fully integrated with the new memory and utils.
"""
from __future__ import annotations
from typing import Dict, Any

from utils.telegram_api import send_message, ask_for_location
from utils.weather_utils import get_weather_forecast_from_google

def handle_weather(user_info: Dict[str, Any], user_text: str) -> None:
    """
    ส่งสภาพอากาศล่าสุดกลับไปยังผู้ใช้
    - ถ้ามี location ในโปรไฟล์ => ตอบทันที
    - ถ้ายังไม่มี => ขอให้ผู้ใช้แชร์ตำแหน่ง
    """
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    profile = user_info['profile']
    
    print(f"[handle_weather] Request from user {user_name} (ID: {chat_id})")

    try:
        # ตรวจสอบว่ามีข้อมูล lat/lon ในโปรไฟล์ของผู้ใช้หรือไม่
        if profile.get("latitude") is not None and profile.get("longitude") is not None:
            lat = profile["latitude"]
            lon = profile["longitude"]
            
            send_message(chat_id, f"🔎 กำลังค้นหาสภาพอากาศสำหรับตำแหน่งที่คุณบันทึกไว้ ({lat:.2f}, {lon:.2f})...")
            
            reply = get_weather_forecast_from_google(lat=lat, lon=lon)
            send_message(chat_id, reply, parse_mode="Markdown")
        else:
            # ถ้าไม่มีตำแหน่งที่บันทึกไว้ ให้ส่งปุ่มขอตำแหน่ง
            ask_for_location(
                chat_id,
                f"📍 คุณ {user_name} ครับ กรุณาแชร์ตำแหน่งของคุณเพื่อให้ผมตรวจสอบสภาพอากาศได้ "
                "จากนั้นลองพิมพ์ /weather อีกครั้งนะครับ"
            )

    except Exception as e:
        print(f"[handle_weather] ERROR: {e}")
        send_message(chat_id, f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลอากาศ: {e}")
