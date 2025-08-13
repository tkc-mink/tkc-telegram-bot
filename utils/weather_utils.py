# utils/weather_utils.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional

try:
    from internal_tools import Google Search
except ImportError:
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data.")
    class M:
        def __init__(self, s): self.snippet = s
    class R:
        def __init__(self, r): self.results = r
    def sm(queries=None): return [R([M("Bangkok: 32°C, Sunny")])]
    Google Search = type("GS", (), {"search": staticmethod(sm)})

def get_weather_forecast_from_google(lat: float, lon: float) -> str:
    query = f"weather at latitude {lat} longitude {lon}"
    try:
        results = Google Search(queries=[query])
        if results and results[0].results and results[0].results[0].snippet:
            data = results[0].results[0].snippet
            return (f"🌤️ **พยากรณ์อากาศล่าสุด**\n---------------------------\n{data}\n---------------------------\n*ข้อมูลจาก Google Weather*")
        return "ขออภัยครับ ไม่สามารถดึงข้อมูลพยากรณ์อากาศได้"
    except Exception as e:
        print(f"[Weather_Utils] ERROR: {e}")
        return "❌ เกิดข้อผิดพลาดในการดึงข้อมูลสภาพอากาศ"
