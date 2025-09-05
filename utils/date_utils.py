# utils/date_utils.py
# -*- coding: utf-8 -*-
"""
Utility สำหรับวันเวลา (tz-aware) พร้อม fallback โซนเวลาเป็น Asia/Bangkok

ฟีเจอร์หลัก
- โซนเวลา: อ่านจากพารามิเตอร์ หรือ ENV: APP_TZ / TIMEZONE / TZ (ดีฟอลต์ Asia/Bangkok)
- ฟังก์ชันเดิม (compatible): now_str, today_str, yesterday_str, is_today, days_between
- เพิ่มตัวช่วยสำคัญ: parse_date, format_date, start_of_day, end_of_day,
  add_days, to_timestamp, from_timestamp, week_range, month_range, human_delta

หมายเหตุ
- ทุกฟังก์ชันพยายามคืนค่าแบบ "ปลอดข้อผิดพลาด" (จับ exception แล้วคืน None/ค่าเหมาะสม)
"""

from __future__ import annotations
from typing import Iterable, List, Optional, Tuple, Union
from datetime import datetime, timedelta, timezone, date
import os

try:
    from zoneinfo import ZoneInfo
except Exception:  # Python <3.9 (ถ้าใช้ backport ไว้ค่อยเปลี่ยนตรงนี้)
    ZoneInfo = None  # type: ignore

# ===== Timezone =====
_DEFAULT_TZ_NAME = "Asia/Bangkok"

def _get_tz(tz: Union[str, timezone, None] = None) -> timezone:
    """คืนค่า tzinfo (อ่านจากพารามิเตอร์ก่อน แล้วค่อย ENV → ดีฟอลต์ Asia/Bangkok)"""
    if isinstance(tz, timezone):
        return tz
    if isinstance(tz, str) and tz:
        return ZoneInfo(tz) if ZoneInfo else timezone.utc
    # จาก ENV
    tzname = os.getenv("APP_TZ") or os.getenv("TIMEZONE") or os.getenv("TZ") or _DEFAULT_TZ_NAME
    try:
        return ZoneInfo(tzname) if ZoneInfo else timezone.utc
    except Exception:
        return timezone.utc

# ===== Core helpers =====
def now(tz: Union[str, timezone, None] = None) -> datetime:
    """คืนเวลาปัจจุบัน (tz-aware)"""
    return datetime.now(_get_tz(tz))

def now_str(fmt: str = "%Y-%m-%d %H:%M:%S", tz: Union[str, timezone, None] = None) -> str:
    """คืนค่าเวลาปัจจุบันในรูปแบบ string ที่กำหนด"""
    try:
        return now(tz).strftime(fmt)
    except Exception:
        return ""

def today_str(fmt: str = "%Y-%m-%d", tz: Union[str, timezone, None] = None) -> str:
    """คืนค่าวันนี้ (ตาม tz)"""
    try:
        return now(tz).strftime(fmt)
    except Exception:
        return ""

def yesterday_str(fmt: str = "%Y-%m-%d", tz: Union[str, timezone, None] = None) -> str:
    """คืนค่าวันเมื่อวาน (ตาม tz)"""
    try:
        return (now(tz) - timedelta(days=1)).strftime(fmt)
    except Exception:
        return ""

# ===== Parsing / Formatting =====
def parse_date(
    value: Union[str, datetime, date],
    fmts: Union[str, Iterable[str]] = ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"),
    tz: Union[str, timezone, None] = None,
) -> Optional[datetime]:
    """
    แปลง string → datetime (tz-aware, ตั้งเวลาเป็น 00:00 หากเป็น date-only)
    รับค่าเป็น datetime/date ตรง ๆ ได้ (จะใส่ tz ให้ถ้ายัง naive)
    """
    try:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=_get_tz(tz))
        if isinstance(value, date):
            dt = datetime(value.year, value.month, value.day)
            return dt.replace(tzinfo=_get_tz(tz))
        if not value:
            return None

        if isinstance(fmts, str):
            fmts = [fmts]

        for f in fmts:
            try:
                dt = datetime.strptime(str(value), f)
                # date-only → set midnight
                if "H" not in f and "M" not in f and "S" not in f:
                    dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                return dt.replace(tzinfo=_get_tz(tz))
            except Exception:
                continue
    except Exception:
        pass
    return None

def format_date(dt: Union[datetime, date, None], fmt: str = "%Y-%m-%d", tz: Union[str, timezone, None] = None) -> str:
    """แปลง datetime/date → string ตามรูปแบบ (ปรับ tz ก่อน)"""
    try:
        if dt is None:
            return ""
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime(dt.year, dt.month, dt.day, tzinfo=_get_tz(tz))
        if dt.tzinfo:
            dt = dt.astimezone(_get_tz(tz))
        else:
            dt = dt.replace(tzinfo=_get_tz(tz))
        return dt.strftime(fmt)
    except Exception:
        return ""

# ===== Checks =====
def is_today(value: Union[str, datetime, date], fmt: str = "%Y-%m-%d", tz: Union[str, timezone, None] = None) -> bool:
    """ตรวจสอบว่า value คือวันนี้ (เทียบตามวันที่ใน tz)"""
    try:
        dt = parse_date(value, fmt, tz)
        if not dt:
            return False
        now_dt = now(tz)
        return (dt.astimezone(_get_tz(tz)).date() == now_dt.date())
    except Exception:
        return False

def is_same_day(a: Union[str, datetime, date], b: Union[str, datetime, date], fmt: str = "%Y-%m-%d", tz: Union[str, timezone, None] = None) -> bool:
    """สองค่าวันเดียวกันไหม (ตาม tz)"""
    try:
        da = parse_date(a, fmt, tz)
        db = parse_date(b, fmt, tz)
        if not da or not db:
            return False
        tzobj = _get_tz(tz)
        return da.astimezone(tzobj).date() == db.astimezone(tzobj).date()
    except Exception:
        return False

# ===== Differences / Ranges =====
def days_between(date1: Union[str, datetime, date], date2: Union[str, datetime, date], fmt: str = "%Y-%m-%d") -> Optional[int]:
    """คืนจำนวนวัน (ค่าสัมบูรณ์) ระหว่างสองวัน โดยเทียบที่ระดับ 'วัน' (ไม่สนเวลา)"""
    try:
        d1 = parse_date(date1, fmt)
        d2 = parse_date(date2, fmt)
        if not d1 or not d2:
            return None
        return abs((d2.date() - d1.date()).days)
    except Exception:
        return None

def human_delta(a: Union[str, datetime], b: Optional[Union[str, datetime]] = None, fmt: str = "%Y-%m-%d %H:%M:%S", tz: Union[str, timezone, None] = None, max_units: int = 2) -> str:
    """
    อธิบายส่วนต่างเวลาแบบอ่านง่าย (เช่น '3 ชั่วโมง 5 นาที')
    """
    try:
        da = parse_date(a, [fmt, "%Y-%m-%d", "%d/%m/%Y"], tz)
        db = parse_date(b, [fmt, "%Y-%m-%d", "%d/%m/%Y"], tz) if b else now(tz)
        if not da or not db:
            return ""
        delta = abs(db - da)
        seconds = int(delta.total_seconds())
        units = []
        for unit_seconds, label in [
            (86400, "วัน"),
            (3600, "ชั่วโมง"),
            (60, "นาที"),
            (1, "วินาที"),
        ]:
            if seconds >= unit_seconds:
                n = seconds // unit_seconds
                units.append(f"{n} {label}")
                seconds %= unit_seconds
            if len(units) >= max_units:
                break
        return " ".join(units) if units else "0 วินาที"
    except Exception:
        return ""

# ===== Day boundaries =====
def start_of_day(value: Optional[Union[str, datetime, date]] = None, tz: Union[str, timezone, None] = None) -> datetime:
    """คืนค่า 00:00:00 ของวันนั้น (tz-aware)"""
    tzobj = _get_tz(tz)
    base = parse_date(value, ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"), tz) if value is not None else now(tzobj)
    base = base.astimezone(tzobj) if base.tzinfo else base.replace(tzinfo=tzobj)
    return base.replace(hour=0, minute=0, second=0, microsecond=0)

def end_of_day(value: Optional[Union[str, datetime, date]] = None, tz: Union[str, timezone, None] = None) -> datetime:
    """คืนค่า 23:59:59.999999 ของวันนั้น (tz-aware)"""
    sod = start_of_day(value, tz)
    return sod.replace(hour=23, minute=59, second=59, microsecond=999999)

# ===== Offsets =====
def add_days(
    value: Union[str, datetime, date, None],
    days: int,
    fmt_in: str = "%Y-%m-%d",
    fmt_out: Optional[str] = "%Y-%m-%d",
    tz: Union[str, timezone, None] = None,
) -> Union[datetime, str, None]:
    """
    บวก/ลบจำนวนวัน
    - ถ้ามี fmt_out → คืน string
    - ถ้า fmt_out=None → คืน datetime
    """
    try:
        base = parse_date(value, [fmt_in, "%Y-%m-%d", "%d/%m/%Y"], tz) if value is not None else now(tz)
        if not base:
            return None
        res = base + timedelta(days=days)
        if fmt_out is None:
            return res
        return format_date(res, fmt_out, tz)
    except Exception:
        return None

# ===== Timestamp =====
def to_timestamp(dt: Union[datetime, str], fmt: str = "%Y-%m-%d %H:%M:%S", tz: Union[str, timezone, None] = None, ms: bool = False) -> Optional[int]:
    """datetime/string → timestamp (วินาทีหรือมิลลิวินาที)"""
    try:
        if not isinstance(dt, datetime):
            dt = parse_date(dt, [fmt, "%Y-%m-%d"], tz)
        if not dt:
            return None
        ts = int(dt.timestamp() * (1000 if ms else 1))
        return ts
    except Exception:
        return None

def from_timestamp(ts: Union[int, float], tz: Union[str, timezone, None] = None) -> Optional[datetime]:
    """timestamp → datetime (tz-aware)"""
    try:
        return datetime.fromtimestamp(float(ts), _get_tz(tz))
    except Exception:
        return None

# ===== Ranges =====
def week_range(value: Optional[Union[str, datetime, date]] = None, tz: Union[str, timezone, None] = None, week_start: int = 0) -> Tuple[datetime, datetime]:
    """
    ช่วงสัปดาห์ของวันที่ให้ (ดีฟอลต์เริ่มวันจันทร์ = 0; อาทิตย์ = 6)
    คืนค่า (start_of_week, end_of_week)
    """
    tzobj = _get_tz(tz)
    base = parse_date(value, ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"), tz) if value else now(tzobj)
    base = base.astimezone(tzobj)
    delta = (base.weekday() - week_start) % 7
    start = (base - timedelta(days=delta)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    return start, end

def month_range(value: Optional[Union[str, datetime, date]] = None, tz: Union[str, timezone, None] = None) -> Tuple[datetime, datetime]:
    """ช่วงเดือน (วันแรก 00:00 ถึงวันสุดท้าย 23:59:59.999999)"""
    tzobj = _get_tz(tz)
    base = parse_date(value, ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"), tz) if value else now(tzobj)
    base = base.astimezone(tzobj)
    start = base.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # วันแรกของเดือนถัดไป - 1 ไมโครวินาที
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    end = next_month - timedelta(microseconds=1)
    return start, end
