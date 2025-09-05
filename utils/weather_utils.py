# utils/weather_utils.py
# -*- coding: utf-8 -*-
"""
Robust weather utility using OpenWeatherMap.

คุณสมบัติ (เสถียร + ครบกว่าเดิม):
- พยายามใช้ One Call (3.0 → 2.5) เพื่อได้รายวัน/แจ้งเตือน ถ้าใช้ไม่ได้ fallback ไป /data/2.5/weather อย่างเดียว
- ดึงชื่อสถานที่ด้วย Reverse Geocoding (Geo API)
- เติมข้อมูลคุณภาพอากาศ (AQI) ได้ (เปิด/ปิดด้วย ENV)
- คืนค่า dict โครงสร้างยืดหยุ่น (location/timezone/current/daily/alerts) ให้ handler ฟอร์แมตสวยงามเอง
- มี retry เบา ๆ, timeout, และข้อความผิดพลาดที่ชัดเจน

ENV ที่ใช้:
- OPENWEATHER_API_KEY          (จำเป็น)
- OPENWEATHER_LANG             ดีฟอลต์ "th"
- OPENWEATHER_UNITS            ดีฟอลต์ "metric"
- OPENWEATHER_TIMEOUT_SEC      ดีฟอลต์ 10
- OPENWEATHER_RETRIES          ดีฟอลต์ 1
- OPENWEATHER_USE_ONECALL      ดีฟอลต์ "1" (เปิด)
- OPENWEATHER_FETCH_AQI        ดีฟอลต์ "1" (เปิด)
- OPENWEATHER_GEO_LOOKUP       ดีฟอลต์ "1" (เปิด)
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Tuple
import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ---------- Config ----------
_LANG   = os.getenv("OPENWEATHER_LANG", "th")
_UNITS  = os.getenv("OPENWEATHER_UNITS", "metric")  # metric/imperial/standard
_TIMEOUT= int(os.getenv("OPENWEATHER_TIMEOUT_SEC", "10"))
_RETRY  = int(os.getenv("OPENWEATHER_RETRIES", "1"))
_USE_ONECALL = os.getenv("OPENWEATHER_USE_ONECALL", "1") == "1"
_FETCH_AQI   = os.getenv("OPENWEATHER_FETCH_AQI", "1") == "1"
_GEO_LOOKUP  = os.getenv("OPENWEATHER_GEO_LOOKUP", "1") == "1"

# ---------- Emoji map ----------
WEATHER_EMOJIS = {
    "Thunderstorm": "⛈️", "Drizzle": "💧", "Rain": "🌧️",
    "Snow": "❄️", "Mist": "🌫️", "Smoke": "💨", "Haze": "🌫️",
    "Dust": "💨", "Fog": "🌫️", "Sand": "💨", "Ash": "💨",
    "Squall": "🌬️", "Tornado": "🌪️", "Clear": "☀️", "Clouds": "☁️",
}

AQI_LABEL = {
    1: "ดีมาก",
    2: "ดี",
    3: "พอใช้",
    4: "แย่",
    5: "อันตราย",
}

# ---------- Helpers ----------
def _req_json(url: str, params: Dict[str, Any], retries: int = _RETRY) -> Optional[Dict[str, Any]]:
    """
    GET JSON with light retry.
    """
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=_TIMEOUT)
            if r.status_code == 401:
                # บอกไปเลยว่า API key ไม่ถูกต้อง
                return {"__error__": "unauthorized", "__status__": 401, "__text__": r.text}
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt >= retries:
                print(f"[weather_utils] HTTP error: {e}")
                return {"__error__": "network", "__text__": str(e)}
            # backoff เบา ๆ
            time.sleep(0.4 * (attempt + 1))
        except Exception as e:
            print(f"[weather_utils] Unexpected error: {e}")
            return {"__error__": "unexpected", "__text__": str(e)}
    return None

def _capitalize_thai(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    return s[0].upper() + s[1:]

def _tz_from_offset(offset_sec: int) -> timezone:
    return timezone(timedelta(seconds=offset_sec))

def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def _date_str_from_unix(ts: int, offset_sec: int) -> str:
    tz = _tz_from_offset(offset_sec)
    return datetime.fromtimestamp(int(ts), tz=tz).strftime("%Y-%m-%d")

def _build_current_from_weather_json(j: Dict[str, Any]) -> Dict[str, Any]:
    """
    สร้าง current block จาก /data/2.5/weather
    """
    weather = (j.get("weather") or [{}])[0]
    main = j.get("main") or {}
    wind = j.get("wind") or {}
    cond_main = weather.get("main") or ""
    cond_desc = _capitalize_thai(weather.get("description") or "")
    emoji = WEATHER_EMOJIS.get(cond_main, "🌡️")

    # wind speed m/s → km/h
    wind_kph = None
    if "speed" in wind:
        v = _safe_float(wind["speed"])
        if v is not None:
            wind_kph = round(v * 3.6, 1)

    cur: Dict[str, Any] = {
        "temp_c": _safe_float(main.get("temp")),
        "feels_like_c": _safe_float(main.get("feels_like")),
        "humidity": _safe_float(main.get("humidity")),
        "condition": f"{emoji} {cond_desc}".strip(),
        "wind_kph": wind_kph,
        "pressure_hpa": _safe_float(main.get("pressure")),
    }
    return cur

def _fetch_reverse_geocode(lat: float, lon: float, key: str) -> Optional[str]:
    if not _GEO_LOOKUP:
        return None
    geo = _req_json(
        "https://api.openweathermap.org/geo/1.0/reverse",
        {"lat": lat, "lon": lon, "limit": 1, "appid": key},
    )
    if not isinstance(geo, list) or not geo:
        return None
    item = geo[0] or {}
    city = item.get("name")
    state = item.get("state")
    country = item.get("country")
    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts) if parts else None

def _fetch_aqi(lat: float, lon: float, key: str) -> Optional[Dict[str, Any]]:
    if not _FETCH_AQI:
        return None
    aqi = _req_json(
        "https://api.openweathermap.org/data/2.5/air_pollution",
        {"lat": lat, "lon": lon, "appid": key},
    )
    if not isinstance(aqi, dict) or not aqi.get("list"):
        return None
    data = (aqi["list"] or [{}])[0]
    idx = data.get("main", {}).get("aqi")  # 1-5
    comp = data.get("components") or {}
    return {
        "aqi": idx,
        "aqi_text": AQI_LABEL.get(idx, "-") if isinstance(idx, int) else None,
        "pm2_5": comp.get("pm2_5"),
        "pm10": comp.get("pm10"),
        "o3": comp.get("o3"),
        "no2": comp.get("no2"),
    }

def _fetch_onecall_any(lat: float, lon: float, key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    พยายามเรียก One Call 3.0 ก่อน → ถ้าไม่ได้ ลอง 2.5 → ถ้ายังไม่ได้ คืน None พร้อมเหตุผล
    """
    if _USE_ONECALL:
        j3 = _req_json(
            "https://api.openweathermap.org/data/3.0/onecall",
            {"lat": lat, "lon": lon, "appid": key, "units": _UNITS, "lang": _LANG},
        )
        if isinstance(j3, dict) and "__error__" not in j3:
            return j3, "3.0"
        # ถ้าผิดสิทธิ์/แพคเกจ มักจะ 401 หรือข้อความพิเศษ → ลอง 2.5 ต่อ
        j25 = _req_json(
            "https://api.openweathermap.org/data/2.5/onecall",
            {"lat": lat, "lon": lon, "appid": key, "units": _UNITS, "lang": _LANG},
        )
        if isinstance(j25, dict) and "__error__" not in j25:
            return j25, "2.5"
        return None, "error"
    return None, "disabled"

def _build_daily_list(onecall: Dict[str, Any]) -> Tuple[list, int, Optional[str]]:
    """
    สร้างรายการพยากรณ์รายวัน (สูงสุด 7–8 วันตามที่ API ให้)
    คืน (list_of_days, timezone_offset_sec, timezone_name)
    """
    tz_offset = int(onecall.get("timezone_offset") or 0)
    tz_name = onecall.get("timezone")
    days = []
    for it in (onecall.get("daily") or [])[:8]:
        temp = it.get("temp") or {}
        weather = (it.get("weather") or [{}])[0]
        cond = _capitalize_thai(weather.get("description") or "")
        main = weather.get("main") or ""
        emoji = WEATHER_EMOJIS.get(main, "")
        pop = it.get("pop")  # 0..1
        if isinstance(pop, (int, float)):
            pop_pct = int(round(float(pop) * 100))
        else:
            pop_pct = None
        days.append({
            "date": _date_str_from_unix(int(it.get("dt", 0)), tz_offset),
            "min": _safe_float(temp.get("min")),
            "max": _safe_float(temp.get("max")),
            "summary": f"{emoji} {cond}".strip(),
            "pop": pop_pct,
        })
    return days, tz_offset, tz_name

def _build_alerts(onecall: Dict[str, Any], tz_offset: int) -> list:
    alerts = []
    for a in (onecall.get("alerts") or []):
        event = a.get("event") or "แจ้งเตือนสภาพอากาศ"
        s = a.get("start")
        e = a.get("end")
        if isinstance(s, int) and isinstance(e, int):
            start = _date_str_from_unix(s, tz_offset)
            end = _date_str_from_unix(e, tz_offset)
            alerts.append(f"{event} ({start}–{end})")
        else:
            alerts.append(str(event))
    return alerts

# ---------- Public API ----------
def get_weather_forecast(lat: float, lon: float) -> Dict[str, Any] | str:
    """
    คืนค่าพยากรณ์อากาศรูปแบบยืดหยุ่น (แนะนำให้ใช้ร่วมกับ handlers/weather.py เวอร์ชันใหม่)
    สำเร็จ → dict:
        {
          "location": "Bangkok, TH",
          "timezone": "Asia/Bangkok" หรือ "UTC+07:00",
          "current": {
              "temp_c": 32.1, "feels_like_c": 37.0, "condition": "☁️ เมฆบางส่วน",
              "humidity": 62, "wind_kph": 9.4, "aqi": 2
          },
          "daily": [ { "date":"2025-09-05", "min":27, "max":33, "summary":"🌧️ ฝนฟ้าคะนอง", "pop":70 }, ... ],
          "alerts": [ "ฝนตกหนัก (2025-09-05–2025-09-06)", ... ]
        }
    ผิดพลาด → str ข้อความที่อ่านรู้เรื่อง (handler จะฟอร์แมตให้อัตโนมัติ)
    """
    api_key = os.getenv("OPENWEATHER_API_KEY") or ""
    if not api_key:
        print("[weather_utils] OPENWEATHER_API_KEY not set")
        return "❌ ขออภัยครับ ระบบพยากรณ์อากาศยังไม่ได้ตั้งค่า API Key"

    if lat is None or lon is None:
        return "❌ ไม่พบพิกัด กรุณาแชร์ตำแหน่งของคุณก่อนนะครับ"

    # --- current weather (ใช้เสมอเพื่อความแม่นยำ + ได้ชื่อเมือง/ประเทศบางส่วน) ---
    current = _req_json(
        "https://api.openweathermap.org/data/2.5/weather",
        {"lat": lat, "lon": lon, "appid": api_key, "units": _UNITS, "lang": _LANG},
    )
    if isinstance(current, dict) and current.get("__error__") == "unauthorized":
        return "❌ API Key ของ OpenWeatherMap ไม่ถูกต้องหรือหมดอายุครับ"
    if not isinstance(current, dict) or current.get("__error__"):
        # network/unexpected → ข้อความอ่านรู้เรื่อง
        return "❌ ขออภัยครับ ไม่สามารถเชื่อมต่อกับบริการพยากรณ์อากาศได้"

    cur_block = _build_current_from_weather_json(current)
    name_from_current = current.get("name")
    # timezone offset จาก endpoint นี้ (วินาที) — ใช้ได้กรณี onecall ใช้ไม่ได้
    tz_offset_from_current = int(current.get("timezone") or 0)

    # --- onecall (รายวัน + timezone name + alerts) ---
    onecall, which = _fetch_onecall_any(lat, lon, api_key)
    days, tz_offset, tz_name = [], tz_offset_from_current, None
    alerts = []
    if isinstance(onecall, dict):
        days, tz_offset, tz_name = _build_daily_list(onecall)
        alerts = _build_alerts(onecall, tz_offset)
    else:
        # no onecall → days ว่าง แต่ยังมี current ใช้งานได้
        pass

    # --- reverse geo (หาชื่อสถานที่) ---
    location_name = name_from_current
    if _GEO_LOOKUP:
        rev = _fetch_reverse_geocode(lat, lon, api_key)
        if rev:
            location_name = rev

    # --- AQI ---
    if _FETCH_AQI:
        aqi = _fetch_aqi(lat, lon, api_key)
        if isinstance(aqi, dict):
            cur_block["aqi"] = aqi.get("aqi")
            cur_block["aqi_text"] = aqi.get("aqi_text")
            # (optionally) แนบค่ารายองค์ประกอบ
            cur_block["aqi_components"] = {
                k: v for k, v in aqi.items() if k in ("pm2_5", "pm10", "o3", "no2")
            }

    # --- timezone string ---
    tz_str = tz_name
    if not tz_str and tz_offset is not None:
        sign = "+" if tz_offset >= 0 else "-"
        hh = abs(tz_offset) // 3600
        mm = (abs(tz_offset) % 3600) // 60
        tz_str = f"UTC{sign}{hh:02d}:{mm:02d}"

    # --- compose result ---
    result: Dict[str, Any] = {
        "location": location_name or f"{lat:.4f},{lon:.4f}",
        "timezone": tz_str,
        "current": cur_block,
        "daily": days,
    }
    if alerts:
        result["alerts"] = alerts

    # แนบเวลาสร้างผลลัพธ์
    try:
        # ใช้ tz_offset (จาก onecall ถ้ามี) เพื่อระบุเวลา ณ ตำแหน่ง
        tz = _tz_from_offset(tz_offset or 0)
        result["generated_at"] = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    return result
