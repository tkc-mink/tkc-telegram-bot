# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching weather data using a robust web scraping method.
This version's function name is corrected to match what other files expect.
"""
from __future__ import annotations
import requests
from bs4 import BeautifulSoup

def get_weather_forecast_from_scraping(lat: float, lon: float) -> str:
    """
    Fetches a weather forecast by scraping Google Weather results.
    """
    print(f"[Weather_Utils] Scraping weather for Lat: {lat}, Lon: {lon}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://www.google.com/search?q=weather+at+{lat},{lon}&hl=th"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        location = soup.find('div', {'id': 'wob_loc'}).text
        temp = soup.find('span', {'id': 'wob_tm'}).text
        condition = soup.find('span', {'id': 'wob_dc'}).text
        
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
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลสภาพอากาศ"
