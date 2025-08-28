# handlers/weather.py
# -*- coding: utf-8 -*-
"""
Handler for fetching weather, now fully integrated with the final API-based utility.
"""
from __future__ import annotations
from typing import Dict, Any

from utils.telegram_api import send_message, ask_for_location
# ✅ **ส่วนที่แก้ไข:** เปลี่ยนไป import ฟังก์ชันชื่อที่ถูกต้อง
from utils.weather_utils import get_weather_forecast

def handle_weather(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Sends the latest weather forecast to the user.
    - If location is in profile => responds immediately.
    - If not => asks the user to share their location.
    """
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    profile = user_info['profile']
    
    print(f"[handle_weather] Request from user {user_name} (ID: {chat_id})")

    try:
        # Check if lat/lon data exists in the user's profile
        if profile.get("latitude") is not None and profile.get("longitude") is not None:
            lat = profile["latitude"]
            lon = profile["longitude"]
            
            send_message(chat_id, f"🔎 กำลังค้นหาสภาพอากาศสำหรับตำแหน่งที่คุณบันทึกไว้...")
            
            # ✅ **ส่วนที่แก้ไข:** เรียกใช้ฟังก์ชันด้วยชื่อที่ถูกต้อง
            reply = get_weather_forecast(lat=lat, lon=lon)
            send_message(chat_id, reply, parse_mode="Markdown")
        else:
            # If no saved location, send a button to request location
            ask_for_location(
                chat_id,
                f"📍 คุณ {user_name} ครับ กรุณาแชร์ตำแหน่งของคุณเพื่อให้ผมตรวจสอบสภาพอากาศได้ "
                "จากนั้นลองพิมพ์ /weather อีกครั้งนะครับ"
            )

    except Exception as e:
        print(f"[handle_weather] An unhandled error occurred: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดในการดึงข้อมูลอากาศครับ")
