# utils/review_utils.py
"""
Utility สำหรับจัดการรีวิว (คะแนน 1-5 ต่อวัน/ต่อผู้ใช้)
- เก็บข้อมูลในไฟล์ JSON (แบ่งตามวันที่)
- มีฟังก์ชันเช็กว่าควรถามรีวิววันนี้ไหม (ดูการใช้งานเมื่อวาน + วันนี้ยังไม่รีวิว)
"""

from __future__ import annotations
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

# -------------------- CONFIG --------------------
REVIEW_FILE = os.getenv("REVIEW_FILE", "review.json")
USAGE_FILE  = os.getenv("USAGE_FILE",  "usage.json")

# ล็อกสำหรับเขียนไฟล์ให้ปลอดภัยเวลามีหลาย thread
_FILE_LOCK = threading.Lock()

# -------------------- IO HELPERS ----------------
def _load_json(path: str) -> Dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[review_utils] load error ({path}): {e}")
        return {}

def _save_json(data: Dict, path: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[review_utils] save error ({path}): {e}")

# -------------------- CORE APIS -----------------
def set_review(user_id: str | int, rating: int) -> None:
    """
    บันทึกคะแนนรีวิว (1-5) ให้ user_id ในวันที่วันนี้
    ถ้า rating เกินช่วงจะถูก clamp ให้อยู่ในช่วง 1-5
    """
    user_id = str(user_id)
    rating  = max(1, min(5, int(rating)))
    today   = _today()

    with _FILE_LOCK:
        data = _load_json(REVIEW_FILE)
        data.setdefault(today, {})
        data[today][user_id] = rating
        _save_json(data, REVIEW_FILE)

def get_review(date: str, user_id: str | int) -> Optional[int]:
    """
    คืนคะแนนรีวิวของ user_id ในวันที่กำหนด (เช่น '2025-07-23')
    ถ้าไม่มีคืน None
    """
    user_id = str(user_id)
    data = _load_json(REVIEW_FILE)
    val = data.get(date, {}).get(user_id)
    return int(val) if val is not None else None

def has_reviewed_today(user_id: str | int) -> bool:
    """True ถ้าผู้ใช้รีวิวแล้วในวันนี้"""
    return get_review(_today(), user_id) is not None

def need_review_today(user_id: str | int) -> bool:
    """
    True ถ้าควรขอให้ user รีวิววันนี้
    เงื่อนไข: ผู้ใช้ใช้งาน "เมื่อวาน" (มี usage log) และวันนี้ยังไม่รีวิว
    """
    user_id   = str(user_id)
    yesterday = _yesterday()

    try:
        usage = _load_json(USAGE_FILE)
        used_yesterday = user_id in usage.get(yesterday, {})
        if used_yesterday and not has_reviewed_today(user_id):
            return True
    except Exception as e:
        print(f"[review_utils] need_review_today error: {e}")
    return False

# -------------------- EXTRA HELPERS (optional) ---
def get_today_avg() -> float:
    """คะแนนเฉลี่ยวันนี้ (ถ้าไม่มีรีวิวจะคืน 0.0)"""
    data = _load_json(REVIEW_FILE)
    today = _today()
    todays = data.get(today, {})
    if not todays:
        return 0.0
    return sum(todays.values()) / len(todays)

def get_day_stats(date: str) -> Dict[str, float]:
    """
    สถิติของวันใดวันหนึ่ง
    return: {"count": n, "avg": x.xx}
    """
    data = _load_json(REVIEW_FILE)
    day = data.get(date, {})
    if not day:
        return {"count": 0, "avg": 0.0}
    return {"count": len(day), "avg": sum(day.values()) / len(day)}

# -------------------- INTERNAL DATE HELPERS -----
def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
