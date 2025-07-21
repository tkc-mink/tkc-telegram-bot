import os
import requests
from datetime import datetime

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_by_coords(lat, lon):
    """
    ดึงข้อมูลสภาพอากาศปัจจุบัน + พยากรณ์ล่วงหน้า 7 วัน ด้วย OpenWeather One Call API 3.0
    :param lat: ละติจูด (float)
    :param lon: ลองจิจูด (float)
    :return: dict ข้อมูล JSON หรือ None ถ้าข้อผิดพลาด
    """
    if not OPENWEATHER_API_KEY:
        print("[OpenWeather] Missing API key")
        return None
    
    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}&exclude=minutely,hourly,alerts"
        f"&units=metric&lang=th&appid={OPENWEATHER_API_KEY}"
    )
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[OpenWeather] API error {response.status_code}: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"[OpenWeather] Request exception: {e}")
        return None

def format_weather_summary(weather_data):
    """
    สร้างข้อความสรุปสภาพอากาศจากข้อมูล JSON
    :param weather_data: dict JSON จาก get_weather_by_coords()
    :return: str สรุปอากาศ
    """
    if not weather_data:
        return "❌ ขออภัยครับ ไม่สามารถดึงข้อมูลสภาพอากาศได้ในขณะนี้"

    current = weather_data.get("current", {})
    daily = weather_data.get("daily", [])

    temp = current.get("temp", "ไม่ทราบ")
    weather_desc = current.get("weather", [{}])[0].get("description", "ไม่ทราบ")
    humidity = current.get("humidity", "ไม่ทราบ")
    wind_speed = current.get("wind_speed", "ไม่ทราบ")

    msg = f"🌤️ สภาพอากาศปัจจุบัน:\nอุณหภูมิ {temp}°C, {weather_desc}\n"
    msg += f"ความชื้น {humidity}% ลม {wind_speed} เมตร/วินาที\n\n"
    
    if daily:
        msg += "📅 พยากรณ์อากาศ 7 วันข้างหน้า:\n"
        for day in daily[:7]:
            dt = day.get("dt")
            temp_min = day.get("temp", {}).get("min", "ไม่ทราบ")
            temp_max = day.get("temp", {}).get("max", "ไม่ทราบ")
            desc = day.get("weather", [{}])[0].get("description", "ไม่ทราบ")
            date_str = datetime.utcfromtimestamp(dt).strftime("%a, %d %b") if dt else "ไม่ระบุวัน"
            msg += f"{date_str}: {desc}, {temp_min}°C - {temp_max}°C\n"
    else:
        msg += "❌ ไม่พบข้อมูลพยากรณ์อากาศล่วงหน้า\n"

    return msg
