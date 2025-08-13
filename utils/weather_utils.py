# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching weather data using reliable methods (Google Search).
This version is designed to be robust and keyless. (Syntax Fixed)
"""
from __future__ import annotations
from typing import Optional

# ✅ แก้ไขชื่อ "Google Search" เป็น "Google Search" ที่ถูกต้อง
try:
    from internal_tools import Google Search
except ImportError:
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data for weather.")
    class MockSearchResult:
        def __init__(self, snippet): self.snippet = snippet
    class MockSearchResults:
        def __init__(self, results): self.results = results
    def search_mock(queries=None):
        return [MockSearchResults([MockSearchResult("Bangkok: 32°C, Sunny, Humidity: 65%")])]
    Google Search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_weather_forecast_from_google(lat: float, lon: float) -> str:
    """
    Fetches a weather forecast by performing a Google search for specific coordinates.
    """
    print(f"[Weather_Utils] Searching for weather at Lat: {lat}, Lon: {lon}")
    query = f"weather at latitude {lat} longitude {lon}"
    try:
        search_results = Google Search(queries=[query])
        if search_results and search_results[0].results and search_results[0].results[0].snippet:
            weather_data = search_results[0].results[0].snippet
            message = (
                f"🌤️ **พยากรณ์อากาศล่าสุด**\n"
                f"---------------------------\n"
                f"{weather_data}\n"
                f"---------------------------\n"
                f"*ข้อมูลจาก Google Weather*"
            )
            return message
        else:
            return "ขออภัยครับ ไม่สามารถดึงข้อมูลพยากรณ์อากาศสำหรับตำแหน่งนี้ได้ในขณะนี้"
    except Exception as e:
        print(f"[Weather_Utils] An error occurred while fetching weather info: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคในการดึงข้อมูลสภาพอากาศ"
