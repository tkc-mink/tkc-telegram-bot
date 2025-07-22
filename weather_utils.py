import os
import re
import requests
from datetime import datetime
from typing import Optional, Tuple, Any

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_LAT, DEFAULT_LON = 13.736717, 100.523186

def get_weather_by_coords(lat: float, lon: float) -> Optional[dict[str, Any]]:
    if not OPENWEATHER_API_KEY:
        return None
    url = (
        f"https://api.openweathermap.org/data/2.5/onecall?"
        f"lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&lang=th"
        f"&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        return resp.json() if resp.status_code == 200 else None
    except:
        return None

def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    if not OPENWEATHER_API_KEY:
        return None
    url = (
        f"http://api.openweathermap.org/geo/1.0/direct?"
        f"q={requests.utils.quote(city)}&limit=1&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]["lat"], data[0]["lon"]
    except:
        pass
    return None

def format_weather_summary(data: dict[str, Any]) -> str:
    if not data: return "❌ ขออภัย ดึงข้อมูลอากาศไม่สำเร็จ"
    cur = data.get("current", {})
    t = cur.get("temp", "–")
    desc = cur.get("weather", [{}])[0].get("description", "–")
    hum = cur.get("humidity", "–")
    wind = cur.get("wind_speed", "–")
    msg = f"🌤️ ขณะนี้ {desc}, {t}°C\nความชื้น {hum}%, ลม {wind} ม./วินาที\n\n"

    daily = data.get("daily", [])
    if daily:
        msg += "📅 พยากรณ์ 7 วัน:\n"
        for d in daily[:7]:
            date = datetime.utcfromtimestamp(d["dt"]).strftime("%a, %d %b")
            tmin = d["temp"]["min"]
            tmax = d["temp"]["max"]
            w = d["weather"][0]["description"]
            msg += f"{date}: {w}, {tmin}°C–{tmax}°C\n"
    return msg

def get_weather_forecast(text: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    if lat and lon:
        return format_weather_summary(get_weather_by_coords(lat, lon) or {})
    city = None
    if text:
        m = re.search(r"(ที่|in)\s*([ก-๙A-Za-z\s]+)", text)
        if m:
            city = m.group(2).strip()
    if city:
        coords = geocode_city(city)
        if coords:
            return format_weather_summary(get_weather_by_coords(*coords) or {})
    return "⚠️ ใช้กรุงเทพฯ เป็นค่าเริ่มต้น:\n" + format_weather_summary(get_weather_by_coords(DEFAULT_LAT, DEFAULT_LON) or {})
