# handlers/weather.py
# -*- coding: utf-8 -*-
"""
Handler for fetching weather, fully integrated with the final API-based utility.
Stable + safe:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo + typing action + ask_for_location)
- รองรับพิกัดจากโปรไฟล์ และกรณีผู้ใช้พิมพ์พิกัดมากับคำสั่ง (lat,lon)
- parse_mode=HTML พร้อม escape ข้อความภายนอก
- รองรับผลลัพธ์จาก get_weather_forecast() ทั้ง str / dict (โครงสร้างยืดหยุ่น)
"""
from __future__ import annotations
from typing import Dict, Any, Iterable, List, Optional, Tuple
import re

from utils.message_utils import send_message, send_typing_action, ask_for_location
from utils.weather_utils import get_weather_forecast


# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_COORD_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)"
)

def _extract_coords_from_text(text: str) -> Optional[Tuple[float, float]]:
    """
    ดึงพิกัดจากข้อความ เช่น:
    '/weather 13.7563,100.5018' หรือ 'อากาศ 18.79 98.98'
    คืน (lat, lon) หรือ None ถ้าไม่พบ
    """
    if not text:
        return None
    m = _CORD_SEARCH = _COORD_RE.search(text)
    if not m:
        return None
    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        # sanity check แบบหยาบ ๆ
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return (lat, lon)
    except Exception:
        return None

def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _fmt_temp_block(cur: Dict[str, Any]) -> str:
    """
    หยิบ temp/feels_like/condition จาก current weather ในรูปแบบยืดหยุ่น
    รองรับคีย์: temp_c/temp/temperature, feels_like/feels_like_c, condition/summary/text
    """
    t = _first_present(cur, ("temp_c", "temperature_c", "temp", "temperature", "temp_f"))
    # แปลงฟาเรนไฮต์เป็น °C ถ้า util คืน temp_f มา
    try:
        if t is not None and "temp_f" in cur and "temp_c" not in cur:
            # ถ้า t น่าจะเป็นฟาเรนไฮต์ ให้ลองแปลง
            tv = float(str(t).replace(",", ""))
            if  t > 60:  # คร่าว ๆ: ฟาเรนไฮต์มัก > 60
                t = round((tv - 32) * 5 / 9, 1)
    except Exception:
        pass

    fl = _first_present(cur, ("feels_like_c", "feels_like", "feelslike_c", "apparent_temperature"))
    cond = _first_present(cur, ("condition", "summary", "text", "weather"))
    hum = _first_present(cur, ("humidity", "rh"))
    wind = _first_present(cur, ("wind_kph", "wind_mps", "wind_speed", "wind"))
    aqi = _first_present(cur, ("aqi", "air_quality"))

    parts: List[str] = []
    if t is not None:
        parts.append(f"<b>{_html_escape(str(t))}°C</b>")
    if fl not in (None, ""):
        parts.append(f"รู้สึกเหมือน {_html_escape(str(fl))}°C")
    if cond:
        parts.append(_html_escape(str(cond)))
    if hum not in (None, ""):
        parts.append(f"ความชื้น {_html_escape(str(hum))}%")
    if wind not in (None, ""):
        parts.append(f"ลม {_html_escape(str(wind))}")
    if aqi not in (None, ""):
        parts.append(f"AQI {_html_escape(str(aqi))}")
    return " · ".join(parts) if parts else "—"

def _fmt_daily_item(it: Dict[str, Any]) -> str:
    """
    แสดง 1 วันแบบยืดหยุ่น:
    รองรับคีย์: date/day/dt, min/temp_min/low_c, max/temp_max/high_c, summary/condition, pop/rain_chance
    """
    day = _first_present(it, ("date", "day", "dt"))
    tmin = _first_present(it, ("min", "temp_min", "low_c", "tmin_c", "min_c"))
    tmax = _first_present(it, ("max", "temp_max", "high_c", "tmax_c", "max_c"))
    summ = _first_present(it, ("summary", "condition", "text"))
    pop  = _first_present(it, ("pop", "rain_chance", "precip_probability"))

    bits: List[str] = []
    if day:
        bits.append(f"<code>{_html_escape(str(day))}</code>")
    if tmin not in (None, "") or tmax not in (None, ""):
        if tmin not in (None, "") and tmax not in (None, ""):
            bits.append(f"{_html_escape(str(tmin))}–{_html_escape(str(tmax))}°C")
        elif tmax not in (None, ""):
            bits.append(f"สูงสุด {_html_escape(str(tmax))}°C")
        else:
            bits.append(f"ต่ำสุด {_html_escape(str(tmin))}°C")
    if summ:
        bits.append(_html_escape(str(summ)))
    if pop not in (None, ""):
        bits.append(f"ฝน {_html_escape(str(pop))}%")

    return " • ".join(bits) if bits else "—"

def _format_weather_dict(d: Dict[str, Any], lat: float, lon: float) -> str:
    """
    ฟอร์แมตผลลัพธ์จาก dict ยืดหยุ่น:
    รองรับคีย์ยอดนิยม:
      - location/place/name/city/resolved_name
      - timezone
      - current/now/today/current_weather (dict)
      - forecast/daily/days (list[dict])
      - alerts/notes (list[str] หรือ str)
    """
    loc = _first_present(d, ("location", "place", "name", "city", "resolved_name", "address"))
    tz  = _first_present(d, ("timezone", "tz"))
    cur = _first_present(d, ("current", "now", "today", "current_weather"))

    lines: List[str] = []
    title = "⛅️ <b>พยากรณ์อากาศ</b>"
    if loc:
        title += f" — <code>{_html_escape(str(loc))}</code>"
    lines.append(title)

    if tz:
        lines.append(f"🕒 เขตเวลา: <code>{_html_escape(str(tz))}</code>")

    # Current
    if isinstance(cur, dict):
        lines.append("• ตอนนี้: " + _fmt_temp_block(cur))

    # Forecast list
    days = _first_present(d, ("forecast", "daily", "days"))
    if isinstance(days, list) and days:
        lines.append("")
        for it in days[:5]:  # จำกัด 5 วัน
            if isinstance(it, dict):
                lines.append("• " + _fmt_daily_item(it))

    # Alerts/notes
    alerts = _first_present(d, ("alerts", "notes"))
    if isinstance(alerts, list) and alerts:
        lines.append("")
        lines.append("<b>แจ้งเตือน</b>")
        for a in alerts[:5]:
            lines.append("• " + _html_escape(str(a)))
    elif isinstance(alerts, str) and alerts.strip():
        lines.append("")
        lines.append("<b>แจ้งเตือน</b>")
        lines.append("• " + _html_escape(alerts.strip()))

    # Footer: coords
    lines.append(f"\n📍 lat={lat:.5f}, lon={lon:.5f}")
    return "\n".join(lines)

def _send_weather_payload(chat_id: int | str, payload: Any, lat: float, lon: float) -> None:
    """
    ส่งข้อความตามชนิด payload:
    - dict → ฟอร์แมตละเอียด
    - str  → ถ้าเป็น HTML อยู่แล้วส่งตรง; ไม่งั้นห่อหัวเรื่อง
    - อื่น ๆ → ข้อความมาตรฐาน
    """
    if isinstance(payload, dict):
        send_message(chat_id, _format_weather_dict(payload, lat, lon), parse_mode="HTML")
        return

    if isinstance(payload, str):
        s = payload.strip()
        if not s:
            send_message(chat_id, "⚠️ ไม่พบข้อมูลอากาศในขณะนี้ครับ", parse_mode="HTML")
            return
        if any(tag in s for tag in ("</", "<b>", "<i>", "<code>", "<a ", "<br")):
            send_message(chat_id, s, parse_mode="HTML")
        else:
            send_message(
                chat_id,
                f"⛅️ <b>พยากรณ์อากาศ</b>\n\n{_html_escape(s)}\n\n📍 lat={lat:.5f}, lon={lon:.5f}",
                parse_mode="HTML",
            )
        return

    send_message(chat_id, "⚠️ ไม่พบข้อมูลอากาศในขณะนี้ครับ", parse_mode="HTML")


# ===== Main Entry =====
def handle_weather(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Sends the latest weather forecast to the user.
    - ถ้ามีพิกัดในข้อความ → ใช้พิกัดนั้น
    - ถ้าโปรไฟล์มีพิกัด → ใช้พิกัดจากโปรไฟล์
    - ถ้าไม่มี → ขอให้แชร์พิกัดผ่านปุ่ม
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""
    profile = user_info.get("profile", {})

    try:
        # 1) พยายามดึงพิกัดจากข้อความก่อน
        coords = _extract_coords_from_text(user_text or "")
        if coords is None:
            # 2) ใช้พิกัดจากโปรไฟล์ ถ้ามี
            lat = profile.get("latitude")
            lon = profile.get("longitude")
            if lat is not None and lon is not None:
                coords = (float(lat), float(lon))

        # 3) ถ้ายังไม่มีพิกัด → ขอผู้ใช้แชร์ตำแหน่ง
        if not coords:
            ask_for_location(
                chat_id,
                (
                    f"📍 คุณ { _html_escape(user_name) } ครับ "
                    "กรุณาแชร์ตำแหน่งของคุณเพื่อให้ผมตรวจสอบสภาพอากาศได้ "
                    "จากนั้นลองพิมพ์ <code>/weather</code> อีกครั้งนะครับ"
                ),
            )
            return

        lat, lon = coords

        # แจ้งกำลังดึงข้อมูล
        send_typing_action(chat_id, "typing")
        send_message(
            chat_id,
            f"🔎 กำลังค้นหาสภาพอากาศสำหรับตำแหน่งที่ระบุ…\n"
            f"📍 lat=<code>{lat:.5f}</code>, lon=<code>{lon:.5f}</code>",
            parse_mode="HTML",
        )

        # เรียก utility (ให้ util จัดการ source/หน่วย)
        data = get_weather_forecast(lat=lat, lon=lon)

        # ส่งผลลัพธ์ (wrapper จะจัดการแบ่ง ≤4096 อัตโนมัติ)
        _send_weather_payload(chat_id, data, lat, lon)

    except Exception as e:
        print(f"[handle_weather] ERROR: {e}")
        send_message(
            chat_id,
            f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการดึงข้อมูลอากาศครับ",
            parse_mode="HTML",
        )
