# utils/usage_utils.py
# -*- coding: utf-8 -*-
"""
Daily usage quota (stable & backward-compatible)

คุณสมบัติ:
- API เดิม: check_and_increase_usage(user_id, filepath=..., limit=...)
- เพิ่มความเสถียร: ไฟล์ล็อก (cross-process), เขียนแบบ atomic ผ่าน save_json_safe
- ใช้ timezone Asia/Bangkok (ตั้งค่าได้), เก็บย้อนหลังและล้างข้อมูลเก่าอัตโนมัติ
- เพิ่ม get_usage_for(...) สำหรับดึงสถานะโควตาวันนี้
- รองรับรายชื่อผู้ใช้ยกเว้นโควตาผ่าน ENV

ENV ที่ตั้งค่าได้:
- USAGE_FILE (ดีฟอลต์ "usage.json")
- APP_TZ (ดีฟอลต์ "Asia/Bangkok")
- USAGE_KEEP_DAYS (ดีฟอลต์ 14)
- USAGE_LOCK_FILE (ดีฟอลต์ "<USAGE_FILE>.lock")
- USAGE_LOCK_TIMEOUT_SEC (ดีฟอลต์ 8)
- USAGE_LOCK_RETRY_INTERVAL (ดีฟอลต์ 0.2)
- EXEMPT_USER_IDS (เช่น "123,456")
"""

from __future__ import annotations
from typing import Dict, Any, Optional
import os
import time
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from utils.json_utils import load_json_safe, save_json_safe

# -------- Config --------
USAGE_FILE = os.getenv("USAGE_FILE", "usage.json")
APP_TZ = os.getenv("APP_TZ", "Asia/Bangkok")
KEEP_DAYS = int(os.getenv("USAGE_KEEP_DAYS", "14"))

LOCK_FILE = os.getenv("USAGE_LOCK_FILE", USAGE_FILE + ".lock")
LOCK_TIMEOUT_SEC = float(os.getenv("USAGE_LOCK_TIMEOUT_SEC", "8"))
LOCK_RETRY_INTERVAL = float(os.getenv("USAGE_LOCK_RETRY_INTERVAL", "0.2"))

# ยกเว้นโควตา
_EXEMPT_RAW = os.getenv("EXEMPT_USER_IDS", "")
EXEMPT_USER_IDS = {x.strip() for x in _EXEMPT_RAW.split(",") if x.strip()}


# -------- Time helpers --------
def _now_local() -> datetime:
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(APP_TZ))
        except Exception:
            pass
    return datetime.now()

def _today_str() -> str:
    return _now_local().strftime("%Y-%m-%d")


# -------- Light file lock (cross-process) --------
class _FileLock:
    def __init__(self, path: str):
        self.path = path

    def __enter__(self):
        start = time.time()
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, f"{os.getpid()} {time.time()}".encode("utf-8"))
                finally:
                    os.close(fd)
                break  # acquired
            except FileExistsError:
                if (time.time() - start) > LOCK_TIMEOUT_SEC:
                    # กำจัด stale lock หากค้างเกิน timeout x4 หรือ >10s
                    try:
                        st = os.stat(self.path)
                        age = time.time() - st.st_mtime
                        if age > max(LOCK_TIMEOUT_SEC * 4, 10):
                            os.remove(self.path)
                            continue
                    except Exception:
                        pass
                    raise TimeoutError("usage file is locked")
                time.sleep(LOCK_RETRY_INTERVAL)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            os.remove(self.path)
        except Exception:
            pass


# -------- Housekeeping --------
def _purge_old_days(data: Dict[str, Any]) -> None:
    """ลบข้อมูลเก่าที่เกินช่วง KEEP_DAYS (นับจากวันนี้ย้อนหลัง)"""
    try:
        today = _now_local().date()
        to_del = []
        for day_str in list(data.keys()):
            # ข้าม meta key ที่ไม่ใช่วันที่
            try:
                d = datetime.strptime(day_str, "%Y-%m-%d").date()
            except Exception:
                continue
            if (today - d) > timedelta(days=KEEP_DAYS):
                to_del.append(day_str)
        for k in to_del:
            data.pop(k, None)
        # บันทึกเวลาทำความสะอาดล่าสุด
        data.setdefault("_meta", {})["last_cleanup"] = _now_local().isoformat(timespec="seconds")
    except Exception as e:
        print(f"[usage_utils] purge_old_days error: {e}")


# -------- Public API (backward-compatible) --------
def check_and_increase_usage(user_id: str, filepath: str = USAGE_FILE, limit: int = 30) -> bool:
    """
    ตรวจโควตาวันนี้ แล้วเพิ่มการใช้งาน 1 ครั้งหากยังไม่เกินลิมิต
    True = เพิ่มได้ (ยังไม่เต็ม) / False = เต็มแล้ว
    """
    uid = str(user_id)
    if uid in EXEMPT_USER_IDS:
        return True  # ยกเว้นโควตา

    day = _today_str()
    with _FileLock(LOCK_FILE):
        usage = load_json_safe(filepath)
        usage.setdefault(day, {})
        usage_day = usage[day]

        used = int(usage_day.get(uid, 0))
        if used >= int(limit):
            return False

        usage_day[uid] = used + 1
        _purge_old_days(usage)
        save_json_safe(usage, filepath)
        return True


def get_usage_for(user_id: str, filepath: str = USAGE_FILE, limit: int = 30) -> Dict[str, int]:
    """
    คืนสถานะโควตาวันนี้ของผู้ใช้:
    { "used": N, "limit": L, "remaining": max(L-N,0) }
    """
    uid = str(user_id)
    day = _today_str()
    try:
        usage = load_json_safe(filepath)
        used = int(usage.get(day, {}).get(uid, 0))
        lim = int(limit)
        return {"used": used, "limit": lim, "remaining": max(lim - used, 0)}
    except Exception:
        lim = int(limit)
        return {"used": 0, "limit": lim, "remaining": lim}
