# weather_utils.py

import os
import re
import requests
from datetime import datetime

# อ่าน API Key จาก ENV
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

def get_weather_by_coords(lat: float, lon: float) -> dict | None:
    """
    ดึงข้อมูลสภาพอากาศปัจจุบัน + พยากรณ์ล่วงหน้า (7 วัน) ด้วย One Call API 3.0
    :param lat: ละติจูด
    :param lon: ลองจิจูด
    :return: dict JSON หรือ None หากเกิดข้อผิดพลาด
    """
    if not OPENWEATHER_API_KEY:
        print("[weather_utils] Missing OPENWEATHER_API_KEY")
        return None

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall"
        f"?lat={lat}&lon={lon}"
        f"&exclude=minutely,hourly,alerts"
        f"&units=metric&lang=th"
        f"&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        print(f"[weather_utils] API error {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"[weather_utils] RequestException: {e}")
    return None

def geocode_city(city: str) -> tuple[float, float] | None:
    """
    แปลงชื่อเมือง/ตำบล/จังหวัด เป็นพิกัด lat/lon ด้วย Geocoding API ของ OpenWeather
    :param city: ชื่อเมือง เช่น "Bangkok" หรือ "กรุงเทพ"
    :return: (lat, lon) หรือ None
    """
    if not OPENWEATHER_API_KEY:
        return None

    url = (
        f"http://api.openweathermap.org/geo/1.0/direct"
        f"?q={requests.utils.quote(city)}&limit=1"
        f"&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]["lat"], data[0]["lon"]
    except requests.RequestException as e:
        print(f"[weather_utils] Geocoding error: {e}")
    return None

def format_weather_summary(data: dict) -> str:
    """
    สร้างข้อความสรุปสภาพอากาศจาก JSON
    :param data: JSON จาก get_weather_by_coords()
    :return: ข้อความสรุปสำหรับส่ง Telegram
    """
    if not data:
        return "❌ ขออภัย ไม่สามารถดึงข้อมูลสภาพอากาศได้ในขณะนี้"

    # สภาพอากาศปัจจุบัน
    current = data.get("current", {})
    temp    = current.get("temp", "–")
    desc    = current.get("weather", [{}])[0].get("description", "–")
    humid   = current.get("humidity", "–")
    wind    = current.get("wind_speed", "–")

    msg  = f"🌤️ สภาพอากาศปัจจุบัน:\n"
    msg += f"อุณหภูมิ {temp}°C, {desc}\n"
    msg += f"ความชื้น {humid}% ลม {wind} ม./วินาที\n\n"

    # พยากรณ์ 7 วันข้างหน้า
    daily = data.get("daily", [])
    if daily:
        msg += "📅 พยากรณ์ 7 วันข้างหน้า:\n"
        for d in daily[:7]:
            dt   = d.get("dt")
            min_t = d.get("temp", {}).get("min", "–")
            max_t = d.get("temp", {}).get("max", "–")
            ddesc = d.get("weather", [{}])[0].get("description", "–")
            date_str = datetime.utcfromtimestamp(dt).strftime("%a, %d %b") if dt else "–"
            msg += f"{date_str}: {ddesc}, {min_t}°C–{max_t}°C\n"
    else:
        msg += "❌ ไม่พบข้อมูลพยากรณ์อากาศล่วงหน้า\n"

    return msg

def get_weather_forecast(text: str | None = None, lat: float | None = None, lon: float | None = None) -> str:
    """
    ฟังก์ชัน wrapper สำหรับ handlers.py
    :param text: ข้อความจาก user (ใช้ parse เมืองได้)
    :param lat: พิกัดละติจูด (ถ้ามี)
    :param lon: พิกัดลองจิจูด (ถ้ามี)
    :return: ข้อความสรุปอากาศ
    """
    # 1) ถ้ามีพิกัด ให้ดึงตรงไป
    if lat is not None and lon is not None:
        data = get_weather_by_coords(lat, lon)
        return format_weather_summary(data)

    # 2) ถ้าไม่มีพิกัด แต่ user พิมพ์เมืองใน text
    city = None
    if text:
        m = re.search(r"(ที่|in)\s*([ก-๙A-Za-z\s]+)", text)
        if m:
            city = m.group(2).strip()

    # 3) กำหนด default เมือง
    query_city = city or "Bangkok"

    # 4) แปลงเป็นพิกัด
    coords = geocode_city(query_city)
    if coords:
        lat, lon = coords
        data = get_weather_by_coords(lat, lon)
        return format_weather_summary(data)

    # 5) ถ้า geocode ไม่สำเร็จ
    return f"❌ ขออภัย ไม่สามารถหาพิกัดของ '{query_city}' ได้ กรุณาระบุชื่อเมืองหรือแชร์ตำแหน่ง GPS"

