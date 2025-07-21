# weather_utils.py
import os
import requests

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_forecast(text):
    # ดึงจังหวัด/เมืองจาก text (ง่ายสุด: หา "ที่..."/"in ..." หรือ fallback = "Bangkok,th")
    import re
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
            return f"สภาพอากาศที่ {city} : {desc}, อุณหภูมิ {temp}°C, ความชื้น {humid}%"
        else:
            return f"ขออภัย ไม่พบข้อมูลสภาพอากาศของ {city} ครับ"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการค้นหาสภาพอากาศ: {str(e)}"
