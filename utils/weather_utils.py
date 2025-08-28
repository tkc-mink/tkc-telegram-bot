# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching weather data using a robust web scraping method.
This is Plan B to bypass the persistent SyntaxError and ensure functionality.
"""
from __future__ import annotations
from typing import Optional
import requests
from bs4 import BeautifulSoup

def get_weather_forecast_from_google(lat: float, lon: float) -> str:
    """
    Fetches a weather forecast by scraping Google Weather results.
    This method is reliable and does not depend on internal tools.
    """
    print(f"[Weather_Utils] Scraping weather for Lat: {lat}, Lon: {lon}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    # ใช้ Google Weather โดยตรง พร้อมระบุภาษาไทย (hl=th)
    url = f"https://www.google.com/search?q=weather+at+{lat},{lon}&hl=th"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status() # ตรวจสอบว่า request สำเร็จหรือไม่

        soup = BeautifulSoup(resp.text, 'html.parser')

        # ค้นหาข้อมูลจาก ID ของ HTML element ที่ Google ใช้ (ค่อนข้างเสถียร)
        location = soup.find('div', {'id': 'wob_loc'}).text
        temp = soup.find('span', {'id': 'wob_tm'}).text
        condition = soup.find('span', {'id': 'wob_dc'}).text
        
        # จัดรูปแบบข้อความให้สวยงามและอ่านง่าย
        message = (
            f"🌤️ **พยากรณ์อากาศล่าสุด**\n"
            f"---------------------------\n"
            f"**ตำแหน่ง:** {location}\n"
            f"**อุณหภูมิ:** {temp}°C\n"
            f"**สภาพอากาศ:** {condition}\n"
            f"---------------------------\n"
            f"*ข้อมูลจาก Google Weather (Scraping)*"
        )
        return message
    except Exception as e:
        print(f"[Weather_Utils] An error occurred while scraping weather info: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลสภาพอากาศด้วยวิธี Scraping"
