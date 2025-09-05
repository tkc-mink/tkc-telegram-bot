# utils/review_utils.py
# -*- coding: utf-8 -*-
"""
Utility สำหรับจัดการรีวิว (คะแนน 1-5 ต่อวัน/ต่อผู้ใช้)
- จัดเก็บแบบ JSON แยกตามวันที่
- Thread-safe + Atomic write (เขียน .tmp แล้ว os.replace)
- ทนทานต่อไฟล์/JSON เสีย (fallback เป็น {} และ log)
- ปรับแต่งได้ผ่าน ENV

ฟังก์ชันหลัก (Backward-compatible):
- set_review(user_id, rating)
- get_review(date, user_id)
- has_reviewed_today(user_id)
- need_review_today(user_id)

ฟังก์ชันเสริม:
- get_today_avg()
- get_day_stats(date)
- get_reviews_for_date(date)
- get_user_last_review_date(user_id)
- get_overall_stats(date_from=None, date_to=None)
"""

from __future__ import annotations
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import os
import json
import threading

# -------------------- CONFIG --------------------
REVIEW_FILE = os.getenv("REVIEW_FILE", "review.json")
USAGE_FILE  = os.getenv("USAGE_FILE",  "usage.json")

# เกณฑ์ขั้นต่ำของจำนวนข้อความเมื่อวานที่จะ “ขอรีวิว”
MIN_YESTERDAY_USAGE = int(os.getenv("REVIEW_MIN_YESTERDAY_USAGE", "1"))

# ล็อกสำหรับเขียนไฟล์ให้ปลอดภัยเวลามีหลาย thread
_FILE_LOCK = threading.Lock()


# -------------------- DATE HELPERS ----------------
def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def _as_uid(user_id: Any) -> str:
    return str(user_id)


# -------------------- IO HELPERS (robust) --------
def _load_json(path: str) -> Dict:
    """
    อ่าน JSON อย่างทนทาน: ไฟล์หาย/เสีย → คืน {}
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[review_utils] load error ({path}): {e}")
        return {}

def _ensure_parent(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _save_json_atomic(data: Dict, path: str) -> None:
    """
    เขียนไฟล์แบบ atomic: เขียนลง .tmp แล้ว os.replace → ลดความเสี่ยงไฟล์พัง
    """
    try:
        _ensure_parent(path)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[review_utils] save error ({path}): {e}")


# -------------------- USAGE HELPERS ---------------
def _get_usage_count(date: str, user_id: str) -> int:
    """
    คืนจำนวนการใช้งานของ user_id ในวัน date จาก USAGE_FILE
    โครงสร้างที่รองรับ: usage[date][user_id] = count
    """
    try:
        usage = _load_json(USAGE_FILE)
        return int(usage.get(date, {}).get(user_id, 0))
    except Exception as e:
        print(f"[review_utils] usage read error: {e}")
        return 0


# -------------------- CORE APIS -------------------
def set_review(user_id: str | int, rating: int) -> None:
    """
    บันทึกคะแนนรีวิว (1-5) ให้ user_id ในวันที่วันนี้
    ถ้า rating เกินช่วงจะถูก clamp ให้อยู่ในช่วง 1-5
    """
    uid     = _as_uid(user_id)
    rating  = max(1, min(5, int(rating)))
    today   = _today()

    with _FILE_LOCK:
        data = _load_json(REVIEW_FILE)
        data.setdefault(today, {})
        data[today][uid] = rating
        _save_json_atomic(data, REVIEW_FILE)

def get_review(date: str, user_id: str | int) -> Optional[int]:
    """
    คืนคะแนนรีวิวของ user_id ในวันที่กำหนด (เช่น '2025-07-23')
    ถ้าไม่มีคืน None
    """
    uid = _as_uid(user_id)
    data = _load_json(REVIEW_FILE)
    val = data.get(date, {}).get(uid)
    try:
        return int(val) if val is not None else None
    except Exception:
        return None

def has_reviewed_today(user_id: str | int) -> bool:
    """True ถ้าผู้ใช้รีวิวแล้วในวันนี้"""
    return get_review(_today(), user_id) is not None

def need_review_today(user_id: str | int) -> bool:
    """
    True ถ้าควรขอให้ user รีวิววันนี้
    เงื่อนไข:
      - ผู้ใช้มีการใช้งาน "เมื่อวาน" อย่างน้อย MIN_YESTERDAY_USAGE ครั้ง
      - และวันนี้ยังไม่รีวิว
    """
    uid       = _as_uid(user_id)
    yesterday = _yesterday()

    try:
        used_yesterday = _get_usage_count(yesterday, uid)
        if used_yesterday >= MIN_YESTERDAY_USAGE and not has_reviewed_today(uid):
            return True
    except Exception as e:
        print(f"[review_utils] need_review_today error: {e}")
    return False


# -------------------- STATS / INSIGHTS ------------
def get_today_avg() -> float:
    """คะแนนเฉลี่ยวันนี้ (ถ้าไม่มีรีวิวจะคืน 0.0)"""
    data = _load_json(REVIEW_FILE)
    today = _today()
    todays = data.get(today, {})
    if not todays:
        return 0.0
    try:
        vals = [int(v) for v in todays.values()]
        return (sum(vals) / len(vals)) if vals else 0.0
    except Exception:
        return 0.0

def get_day_stats(date: str) -> Dict[str, float]:
    """
    สถิติของวันใดวันหนึ่ง
    return: {"count": n, "avg": x.xx}
    """
    data = _load_json(REVIEW_FILE)
    day = data.get(date, {})
    if not day:
        return {"count": 0, "avg": 0.0}
    try:
        vals = [int(v) for v in day.values()]
        return {"count": float(len(vals)), "avg": (sum(vals) / len(vals)) if vals else 0.0}
    except Exception:
        return {"count": 0.0, "avg": 0.0}

def get_reviews_for_date(date: str) -> Dict[str, int]:
    """
    คืน dict ของรีวิวทั้งวันนั้น: { user_id: rating }
    """
    data = _load_json(REVIEW_FILE)
    day = data.get(date, {})
    out: Dict[str, int] = {}
    for uid, v in day.items():
        try:
            out[str(uid)] = int(v)
        except Exception:
            pass
    return out

def get_user_last_review_date(user_id: str | int) -> Optional[str]:
    """
    คืนวันที่ล่าสุดที่ผู้ใช้รายนี้เคยรีวิว (YYYY-MM-DD) หรือ None ถ้าไม่พบ
    """
    uid = _as_uid(user_id)
    data = _load_json(REVIEW_FILE)
    dates = sorted(data.keys())
    last: Optional[str] = None
    for d in dates:
        try:
            if uid in data.get(d, {}):
                last = d
        except Exception:
            continue
    return last

def get_overall_stats(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    สรุปสถิติช่วงวัน (ปิดท้ายรวม):
      - by_date: {date: {"count": n, "avg": x.xx}}
      - total_count, overall_avg
    ถ้าไม่ระบุช่วง → ครอบคลุมทุกวันที่มีข้อมูล
    """
    data = _load_json(REVIEW_FILE)
    if not data:
        return {"by_date": {}, "total_count": 0, "overall_avg": 0.0}

    # เลือกช่วงวันที่
    dates = sorted(data.keys())
    if date_from:
        dates = [d for d in dates if d >= date_from]
    if date_to:
        dates = [d for d in dates if d <= date_to]

    by_date: Dict[str, Dict[str, float]] = {}
    all_vals: list[int] = []

    for d in dates:
        day = data.get(d, {})
        vals = []
        for v in day.values():
            try:
                vals.append(int(v))
            except Exception:
                pass
        if vals:
            by_date[d] = {"count": float(len(vals)), "avg": sum(vals) / len(vals)}
            all_vals.extend(vals)
        else:
            by_date[d] = {"count": 0.0, "avg": 0.0}

    overall_avg = (sum(all_vals) / len(all_vals)) if all_vals else 0.0
    return {"by_date": by_date, "total_count": len(all_vals), "overall_avg": overall_avg}
