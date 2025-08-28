# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching weather data using the OpenWeatherMap API.
This is the final, most robust, and complete version.
"""
from __future__ import annotations
from typing import Optional
import os
import requests

# Map weather condition codes from OpenWeatherMap to emojis
WEATHER_EMOJIS = {
    "Thunderstorm": "⛈️", "Drizzle": "💧", "Rain": "🌧️",
    "Snow": "❄️", "Mist": "🌫️", "Smoke": "💨", "Haze": "🌫️",
    "Dust": "💨", "Fog": "🌫️", "Sand": "💨", "Ash": "💨",
    "Squall": "🌬️", "Tornado": "🌪️", "Clear": "☀️", "Clouds": "☁️",
}

def get_weather_forecast(lat: float, lon: float) -> str:
    """
    Fetches a detailed weather forecast from the OpenWeatherMap API.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("[Weather_Utils] ERROR: OPENWEATHER_API_KEY is not set.")
        return "❌ ขออภัยครับ ระบบพยากรณ์อากาศยังไม่ได้ตั้งค่า API Key"
    
    if lat is None or lon is None:
        return "❌ ไม่พบพิกัด กรุณาแชร์ตำแหน่งของคุณก่อนนะครับ"

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=th"
    )
    
    print(f"[Weather_Utils] Fetching weather from OpenWeatherMap API for Lat: {lat}, Lon: {lon}")
    
    try:
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 401:
            return "❌ API Key ของ OpenWeatherMap ไม่ถูกต้องหรือหมดอายุครับ"
        
        resp.raise_for_status()
        
        data = resp.json()
        
        weather = data.get("weather", [{}])[0]
        main_condition = weather.get("main", "ไม่ทราบ")
        description = weather.get("description", "-").capitalize()
        emoji = WEATHER_EMOJIS.get(main_condition, "🌡️")

        main = data.get("main", {})
        temp = main.get("temp", "-")
        feels_like = main.get("feels_like", "-")
        humidity = main.get("humidity", "-")
        
        wind = data.get("wind", {})
        wind_speed_kmh = round(wind.get("speed", 0) * 3.6, 1)

        city_name = data.get("name", "ไม่ระบุตำแหน่ง")

        message = (
            f"{emoji} **พยากรณ์อากาศล่าสุด - {city_name}**\n"
            f"------------------------------------\n"
            f"**สภาพอากาศ:** {description}\n"
            f"**อุณหภูมิ:** {temp}°C (รู้สึกเหมือน {feels_like}°C)\n"
            f"**ความชื้น:** {humidity}%\n"
            f"**ความเร็วลม:** {wind_speed_kmh} กม./ชม.\n"
            f"------------------------------------\n"
            f"*ข้อมูลจาก OpenWeatherMap*"
        )
        return message
        
    except requests.exceptions.RequestException as e:
        print(f"[Weather_Utils] Network error fetching weather data: {e}")
        return "❌ ขออภัยครับ ไม่สามารถเชื่อมต่อกับบริการพยากรณ์อากาศได้"
    except Exception as e:
        print(f"[Weather_Utils] An error occurred while processing weather data: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลข้อมูลสภาพอากาศ"
