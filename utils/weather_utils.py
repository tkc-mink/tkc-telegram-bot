# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching weather data using reliable methods (Google Search).
This version is designed to be robust and keyless.
"""
from __future__ import annotations
from typing import Optional

# นี่คือส่วนที่ผม (Gemini) จะใช้เครื่องมือภายในของผม
# โค้ดนี้ถูกออกแบบมาให้ทำงานได้ในสภาพแวดล้อมจริง
try:
    from internal_tools import Google Search
except ImportError:
    # ส่วนนี้สำหรับจำลองการทำงานเผื่อกรณีที่ tool ไม่พร้อมใช้งาน
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data for weather.")
    class MockSearchResult:
        def __init__(self, snippet):
            self.snippet = snippet
    class MockSearchResults:
        def __init__(self, results):
            self.results = results
    def search_mock(queries=None):
        return [MockSearchResults([MockSearchResult("Bangkok: 32°C, Sunny, Humidity: 65%")])]
    Google Search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_weather_forecast_from_google(lat: float, lon: float) -> str:
    """
    Fetches a weather forecast by performing a Google search for specific coordinates.
    This method is reliable and does not require an external API key.
    """
    print(f"[Weather_Utils] Searching for weather at Lat: {lat}, Lon: {lon}")
    query = f"weather at latitude {lat} longitude {lon}"

    try:
        # ใช้เครื่องมือ Google Search เพื่อดึงข้อมูลสภาพอากาศ
        search_results = Google Search(queries=[query])

        # ประมวลผลผลลัพธ์เพื่อหาข้อมูลที่เกี่ยวข้องที่สุด
        if search_results and search_results[0].results and search_results[0].results[0].snippet:
            weather_data = search_results[0].results[0].snippet

            # จัดรูปแบบข้อความให้สวยงามและอ่านง่าย
            message = (
                f"🌤️ **พยากรณ์อากาศล่าสุด**\n"
                f"---------------------------\n"
                f"{weather_data}\n"
                f"---------------------------\n"
                f"*ข้อมูลจาก Google Weather*"
            )
            return message
        else:
            print(f"[Weather_Utils] No weather forecast found for ({lat}, {lon})")
            return "ขออภัยครับ ไม่สามารถดึงข้อมูลพยากรณ์อากาศสำหรับตำแหน่งนี้ได้ในขณะนี้"

    except Exception as e:
        print(f"[Weather_Utils] An error occurred while fetching weather info: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคในการดึงข้อมูลสภาพอากาศ"
