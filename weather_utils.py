# weather_utils.py
import os
import requests
import re

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_forecast(text, lat=None, lon=None):
    if lat and lon:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&lang=th&units=metric"
    else:
        city = "Bangkok"
        m = re.search(r"(ที่|in)\s*([ก-๙a-zA-Z\s]+)", text)
        if m:
            city = m.group(2).strip()
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&lang=th&units=metric"
    try:
        resp = requests.get(url, timeout=7)
        data = resp.json()
        if data.get("cod") == 200:
            desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            humid = data["main"]["humidity"]
            place = data.get("name", city)
            return f"สภาพอากาศที่ {place} : {desc}, อุณหภูมิ {temp}°C, ความชื้น {humid}%"
        else:
            return f"ขออภัย ไม่พบข้อมูลสภาพอากาศครับ"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการค้นหาสภาพอากาศ: {str(e)}"
