import os
import re
import requests
from datetime import datetime
from typing import Optional, Tuple, Any

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DEFAULT_LAT, DEFAULT_LON = 13.736717, 100.523186

def get_weather_by_coords(lat: float, lon: float) -> Optional[dict]:
    """ดึง weather data จาก OpenWeather API (One Call)"""
    if not OPENWEATHER_API_KEY:
        print("[weather_utils] Missing OPENWEATHER_API_KEY")
        return None
    url = (
        f"https://api.openweathermap.org/data/2.5/onecall?"
        f"lat={lat}&lon={lon}&exclude=minutely,hourly,alerts&units=metric&lang=th"
        f"&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        print(f"[weather_utils] API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[weather_utils] RequestException: {e}")
    return None

def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """แปลงชื่อเมืองเป็น lat/lon (OpenWeather geocoding)"""
    if not OPENWEATHER_API_KEY:
        print("[weather_utils] Missing OPENWEATHER_API_KEY for geocode")
        return None
    city = re.sub(r"[^ก-๙a-zA-Z0-9\s]", "", city)  # กรอง input เล็กน้อย
    url = (
        f"http://api.openweathermap.org/geo/1.0/direct?"
        f"q={requests.utils.quote(city)}&limit=1&appid={OPENWEATHER_API_KEY}"
    )
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]["lat"], data[0]["lon"]
    except Exception as e:
        print(f"[weather_utils] Geocoding error: {e}")
    return None

def format_weather_summary(data: dict) -> str:
    """จัดรูปแบบข้อมูลอากาศให้อ่านง่าย"""
    if not data or "current" not in data:
        return "❌ ขออภัย ไม่สามารถดึงข้อมูลสภาพอากาศได้ในขณะนี้"
    cur = data.get("current", {})
    t = cur.get("temp", "–")
    desc = cur.get("weather", [{}])[0].get("description", "–")
    hum = cur.get("humidity", "–")
    wind = cur.get("wind_speed", "–")
    msg = f"🌤️ ขณะนี้ {desc}, {t}°C\nความชื้น {hum}%, ลม {wind} ม./วินาที\n\n"
    daily = data.get("daily", [])
    if daily:
        msg += "📅 พยากรณ์ 7 วันข้างหน้า:\n"
        for d in daily[:7]:
            try:
                date = datetime.utcfromtimestamp(d["dt"]).strftime("%a, %d %b")
                tmin = d.get("temp", {}).get("min", "–")
                tmax = d.get("temp", {}).get("max", "–")
                w = d.get("weather", [{}])[0].get("description", "–")
                msg += f"{date}: {w}, {tmin}°C–{tmax}°C\n"
            except Exception:
                continue
    else:
        msg += "❌ ไม่พบข้อมูลพยากรณ์อากาศล่วงหน้า\n"
    return msg

def get_weather_forecast(text: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """
    คืนผลสภาพอากาศ/พยากรณ์ จาก lat/lon หรือชื่อเมือง (ภาษาไทย/อังกฤษ)
    ถ้าไม่มีข้อมูล ใช้กรุงเทพฯเป็น default
    """
    # 1) ถ้ามีพิกัด → ดึงตรง
    if lat is not None and lon is not None:
        return format_weather_summary(get_weather_by_coords(lat, lon) or {})

    # 2) ถ้ามีชื่อเมือง
    city = None
    if text:
        m = re.search(r"(ที่|in)\s*([ก-๙A-Za-z\s]+)", text)
        if m:
            city = m.group(2).strip()
    if city:
        coords = geocode_city(city)
        if coords:
            return format_weather_summary(get_weather_by_coords(*coords) or {})

    # 3) fallback กรุงเทพฯ
    summary = format_weather_summary(get_weather_by_coords(DEFAULT_LAT, DEFAULT_LON) or {})
    return "⚠️ ใช้กรุงเทพฯ เป็นค่า default:\n" + summary
