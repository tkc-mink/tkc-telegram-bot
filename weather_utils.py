# weather_utils.py

import os
import re
import requests
from datetime import datetime
from typing import Optional, Tuple, Any

# ─── Configuration ────────────────────────────────────────

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
# ถ้าไม่มีพิกัดใดๆ ให้ใช้ กรุงเทพฯ
DEFAULT_LAT, DEFAULT_LON = 13.736717, 100.523186

# ─── Core: One Call v2.5 (ฟรี 1,000 calls/day) ────────────

def get_weather_by_coords(lat: float, lon: float) -> Optional[dict[str, Any]]:
    if not OPENWEATHER_API_KEY:
        print("[weather_utils] Missing OPENWEATHER_API_KEY")
        return None

    url = (
        f"https://api.openweathermap.org/data/2.5/onecall"
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

def geocode_city(city: str) -> Optional[Tuple[float, float]]:
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
            if isinstance(data, list) and data:
                return data[0]["lat"], data[0]["lon"]
    except requests.RequestException as e:
        print(f"[weather_utils] Geocoding error: {e}")
    return None

# ─── Formatter ────────────────────────────────────────────

def format_weather_summary(data: dict[str, Any]) -> str:
    if not data:
        return "❌ ขออภัย ไม่สามารถดึงข้อมูลสภาพอากาศได้ในขณะนี้"

    cur = data.get("current", {})
    t    = cur.get("temp", "–")
    desc = cur.get("weather", [{}])[0].get("description", "–")
    hum  = cur.get("humidity", "–")
    wind = cur.get("wind_speed", "–")

    msg  = f"🌤️ สภาพอากาศปัจจุบัน:\n"
    msg += f"อุณหภูมิ {t}°C, {desc}\n"
    msg += f"ความชื้น {hum}% ลม {wind} ม./วินาที\n\n"

    daily = data.get("daily", [])
    if daily:
        msg += "📅 พยากรณ์ 7 วันข้างหน้า:\n"
        for d in daily[:7]:
            dt    = d.get("dt")
            tmin  = d.get("temp", {}).get("min", "–")
            tmax  = d.get("temp", {}).get("max", "–")
            ddesc = d.get("weather", [{}])[0].get("description", "–")
            date  = datetime.utcfromtimestamp(dt).strftime("%a, %d %b") if dt else "–"
            msg  += f"{date}: {ddesc}, {tmin}°C–{tmax}°C\n"
    else:
        msg += "❌ ไม่พบข้อมูลพยากรณ์อากาศล่วงหน้า\n"

    return msg

# ─── Public Wrapper ──────────────────────────────────────

def get_weather_forecast(
    text: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> str:
    # 1) ถ้ามีพิกัด → ดึงตรง
    if lat is not None and lon is not None:
        return format_weather_summary(get_weather_by_coords(lat, lon) or {})

    # 2) ลอง parse เมืองจาก text
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
