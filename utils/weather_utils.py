# weather_utils.py
"""
Utility สำหรับดึงพยากรณ์อากาศ (ปัจจุบัน + รายชั่วโมง/รายวันสั้น ๆ) จาก OpenWeatherMap
รองรับกรณีส่ง lat/lon มาโดยตรง หรือส่งชื่อเมือง/จังหวัดใน text
"""

import os
import requests
from datetime import datetime, timezone
from typing import Optional, Tuple

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ---------------------------
# Public API
# ---------------------------

def get_weather_forecast(
    text: Optional[str] = None,
    lat:   Optional[float] = None,
    lon:   Optional[float] = None,
    units: str = "metric",
    lang:  str = "th"
) -> str:
    """
    คืนข้อความสรุปอากาศสวย ๆ (ภาษาไทย)
    - ถ้ามี lat/lon จะใช้ onecall โดยตรง
    - ถ้าไม่มี lat/lon จะลอง parse ชื่อเมืองจาก text แล้วค่อยหา lat/lon ผ่าน /geo
    """
    if not OPENWEATHER_API_KEY:
        return "❌ ยังไม่ได้ตั้งค่า OPENWEATHER_API_KEY"

    try:
        if (lat is None or lon is None):
            # พยายามดึง lat/lon จากข้อความ (กรณีผู้ใช้พิมพ์ชื่อเมือง)
            city = _extract_city_from_text(text)
            if not city:
                return "⚠️ โปรดแชร์พิกัด (location) หรือบอกชื่อเมือง/จังหวัดให้ผมรู้ด้วยครับ"
            lat, lon = _geocode_city(city)
            if lat is None or lon is None:
                return f"❌ หาเมือง '{city}' ไม่พบในระบบ OpenWeather"

        data = _call_onecall_api(lat, lon, units=units, lang=lang)
        if not data:
            return "❌ ไม่สามารถดึงข้อมูลอากาศได้ในขณะนี้"

        return _format_weather_message(data, units)
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลอากาศ: {e}"


# ---------------------------
# Internal helpers
# ---------------------------

def _extract_city_from_text(text: Optional[str]) -> Optional[str]:
    """
    ดึงชื่อเมืองแบบง่าย ๆ จากประโยค เช่น "อากาศ กรุงเทพ เป็นไง"
    คุณสามารถปรับ regex ให้ฉลาดขึ้นได้ในอนาคต
    """
    if not text:
        return None
    text = text.strip()
    # ลองตัดคำง่าย ๆ
    # เคสทั่วไป: "อากาศที่กรุงเทพ", "พยากรณ์อากาศ เชียงใหม่"
    for token in ["อากาศที่", "อากาศ", "พยากรณ์อากาศ", "ที่", "weather", "เมือง", "จังหวัด"]:
        text = text.replace(token, "")
    text = text.strip()
    return text if text else None


def _geocode_city(city: str) -> Tuple[Optional[float], Optional[float]]:
    """
    ใช้ OpenWeather Geo API หาพิกัด lat/lon จากชื่อเมือง
    """
    url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "limit": 1
    }
    r = requests.get(url, params=params, timeout=10)
    if not r.ok:
        return None, None
    arr = r.json()
    if not arr:
        return None, None
    return arr[0].get("lat"), arr[0].get("lon")


def _call_onecall_api(lat: float, lon: float, units: str = "metric", lang: str = "th") -> dict:
    """
    เรียก One Call API 3.0 (หรือ 2.5 ถ้าคุณใช้เวอร์ชันเก่า)
    """
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": units,
        "lang": lang,
        "exclude": "minutely,alerts"  # ตัดส่วนที่ไม่ใช้
    }
    r = requests.get(url, params=params, timeout=12)
    if not r.ok:
        return {}
    return r.json()


def _format_weather_message(data: dict, units: str) -> str:
    """
    สร้างข้อความสรุปจากข้อมูล onecall
    """
    current = data.get("current", {})
    hourly  = data.get("hourly", [])[:6]   # 6 ชั่วโมงถัดไป
    daily   = data.get("daily", [])[:3]    # 3 วันข้างหน้า

    unit_temp = "°C" if units == "metric" else "°F"

    # ปัจจุบัน
    temp_now = current.get("temp")
    desc_now = _first_weather_desc(current)
    icon_now = _icon_from_desc(desc_now)
    feels    = current.get("feels_like")
    humidity = current.get("humidity")
    wind     = current.get("wind_speed")

    msg = []
    msg.append(f"⛅ พยากรณ์อากาศตอนนี้\n{icon_now} {desc_now.capitalize()}  {temp_now:.1f}{unit_temp} (รู้สึก {feels:.1f}{unit_temp})")
    msg.append(f"💧 ความชื้น {humidity}%  | 💨 ลม {wind} m/s")

    # รายชั่วโมง
    if hourly:
        msg.append("\n🕒 6 ชั่วโมงถัดไป")
        for h in hourly:
            t   = _ts_to_local(h.get("dt"))
            td  = h.get("temp")
            dsc = _first_weather_desc(h)
            ic  = _icon_from_desc(dsc)
            msg.append(f"• {t:%H:%M}  {ic} {dsc}  {td:.0f}{unit_temp}")

    # รายวัน
    if daily:
        msg.append("\n📅 3 วันข้างหน้า")
        for d in daily:
            t   = _ts_to_local(d.get("dt"))
            temp_d = d.get("temp", {})
            tmin = temp_d.get("min")
            tmax = temp_d.get("max")
            dsc = _first_weather_desc(d)
            ic  = _icon_from_desc(dsc)
            msg.append(f"• {t:%a %d/%m}  {ic} {dsc}  {tmin:.0f}-{tmax:.0f}{unit_temp}")

    return "\n".join(msg)


def _first_weather_desc(block: dict) -> str:
    """ดึงคำอธิบายสภาพอากาศตัวแรก"""
    we = block.get("weather", [])
    if we:
        return we[0].get("description", "")
    return ""


def _icon_from_desc(desc: str) -> str:
    """
    map คำอธิบาย -> อีโมจิคร่าว ๆ
    """
    desc = desc.lower()
    if any(k in desc for k in ["rain", "ฝน"]):
        return "🌧️"
    if any(k in desc for k in ["storm", "พายุ", "thunder"]):
        return "⛈️"
    if any(k in desc for k in ["cloud", "เมฆ"]):
        return "☁️"
    if any(k in desc for k in ["snow", "หิมะ"]):
        return "❄️"
    if any(k in desc for k in ["clear", "แจ่มใส"]):
        return "☀️"
    return "🌤️"


def _ts_to_local(ts: int) -> datetime:
    """
    แปลง UNIX ts -> datetime local (ใช้ timezone จากข้อมูลใน onecall เลยก็ได้
    แต่ onecall 3.0 ไม่คืน offset ชัดเจนแล้ว ใช้ tz=UTC แล้วให้ผู้ใช้ตีความเวลาเองก็ได้
    ที่นี่เราจะใช้ UTC+7 แบบฮาร์ดโค้ด หรือจะปรับเองก็ได้
    """
    # ใช้เวลาไทย +7 ชัวร์ ๆ
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
