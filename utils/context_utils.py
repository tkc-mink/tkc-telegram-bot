# utils/context_utils.py
# -*- coding: utf-8 -*-
"""
จัดการ context / usage / location สำหรับผู้ใช้ (Stable & Backward-Compatible)

คุณสมบัติ:
- โควตาประจำวัน (แยกข้อความ/รูป) ต่อผู้ใช้ ต่อวัน + ไฟล์ล็อกกันชนกันหลายโปรเซส
- เขียนไฟล์แบบ atomic (.tmp → os.replace) ป้องกันไฟล์พัง
- เก็บย้อนหลัง/ล้างข้อมูลเก่าอัตโนมัติ
- อัปเกรดสคีมา usage เดิมอัตโนมัติ (int) → โครงสร้างใหม่ {"users": {uid: {"text","image"}}}
- คงฟังก์ชันเดิม: check_and_increase_usage, get_usage_for, update_context, is_waiting_review ฯลฯ
- context สองแบบ: แบบเก่า list[str] และแบบใหม่ list[{"role","content"}]
- รองรับ location + alias ชื่อเดิม update_user_location()

ENV สำคัญ (มีค่าเริ่มต้นให้):
- USAGE_FILE (default: "usage.json")             # ไฟล์โควตรวม (ใหม่)
- APP_TZ (default: "Asia/Bangkok")
- USAGE_TEXT_DAILY_LIMIT (default: 60)
- USAGE_IMAGE_DAILY_LIMIT (default: 15)
- USAGE_KEEP_DAYS (default: 14)
- USAGE_LOCK_FILE (default: "<USAGE_FILE>.lock")
- USAGE_LOCK_TIMEOUT_SEC (default: 8)
- USAGE_LOCK_RETRY_INTERVAL (default: 0.2)
- EXEMPT_USER_IDS (เช่น "123,456")
- (Compat legacy files — จะเขียนสำรองไว้ด้วยเพื่อความเข้ากันได้)
  - LEGACY_USAGE_FILE (default: "usage.json")         # นับข้อความแบบเดิม (int)
  - LEGACY_IMAGE_USAGE_FILE (default: "image_usage.json")
  - WRITE_LEGACY_USAGE_FILES (default: "1")
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os
import json
import time
from datetime import datetime, timedelta

# -------- Timezone --------
try:
    from zoneinfo import ZoneInfo  # py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

# -------- Files (context & location) --------
CONTEXT_FILE       = os.getenv("CONTEXT_FILE", "context_history.json")     # list[str] แบบเดิม
CONTEXT_MSG_FILE   = os.getenv("CONTEXT_MSG_FILE", "context_messages.json")# list[{"role","content"}]
LOCATION_FILE      = os.getenv("LOCATION_FILE", "location_logs.json")

# -------- Usage (new consolidated) --------
USAGE_FILE         = os.getenv("USAGE_FILE", "usage.json")
APP_TZ             = os.getenv("APP_TZ", "Asia/Bangkok")
TEXT_LIMIT_DEFAULT = int(os.getenv("USAGE_TEXT_DAILY_LIMIT", os.getenv("MAX_QUESTION_PER_DAY", "60")))
IMAGE_LIMIT_DEFAULT= int(os.getenv("USAGE_IMAGE_DAILY_LIMIT", os.getenv("MAX_IMAGE_PER_DAY", "15")))
KEEP_DAYS          = int(os.getenv("USAGE_KEEP_DAYS", "14"))
LOCK_FILE          = os.getenv("USAGE_LOCK_FILE", USAGE_FILE + ".lock")
LOCK_TIMEOUT_SEC   = float(os.getenv("USAGE_LOCK_TIMEOUT_SEC", "8"))
LOCK_RETRY_INTERVAL= float(os.getenv("USAGE_LOCK_RETRY_INTERVAL", "0.2"))

# -------- Legacy usage files (optional mirror for backward compatibility) --------
LEGACY_USAGE_FILE        = os.getenv("LEGACY_USAGE_FILE", "usage.json")
LEGACY_IMAGE_USAGE_FILE  = os.getenv("LEGACY_IMAGE_USAGE_FILE", "image_usage.json")
WRITE_LEGACY_USAGE_FILES = os.getenv("WRITE_LEGACY_USAGE_FILES", "1") == "1"

# -------- Exempt users --------
_exempt_raw = os.getenv("EXEMPT_USER_IDS", "")
EXEMPT_USER_IDS: set[str] = {x.strip() for x in _exempt_raw.split(",") if x.strip()}

# ====================== JSON helpers ======================
def _ensure_parent_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _load_json(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[context_utils] load_json({path}) error: {e}")
        return {}

def _save_json_atomic(path: str, data: dict) -> None:
    try:
        _ensure_parent_dir(path)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[context_utils] save_json_atomic({path}) error: {e}")

# ====================== Lock (cross-process) ======================
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
                    try:
                        st = os.stat(self.path)
                        age = time.time() - st.st_mtime
                        if age > max(LOCK_TIMEOUT_SEC * 4, 10):
                            os.remove(self.path)  # stale lock
                            continue
                    except Exception:
                        pass
                    raise TimeoutError("usage lock busy")
                time.sleep(LOCK_RETRY_INTERVAL)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            os.remove(self.path)
        except Exception:
            pass

# ====================== Time helpers ======================
def _now_local() -> datetime:
    if ZoneInfo:
        try:
            return datetime.now(ZoneInfo(APP_TZ))
        except Exception:
            pass
    return datetime.now()

def _today_str() -> str:
    return _now_local().strftime("%Y-%m-%d")

# ====================== Usage data helpers ======================
def _is_date_str(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

def _purge_old_days(data: Dict[str, Any]) -> None:
    """ลบข้อมูลเก่าเกิน KEEP_DAYS"""
    days = [k for k in data.keys() if _is_date_str(k)]
    days.sort(reverse=True)
    for d in days[KEEP_DAYS:]:
        data.pop(d, None)
    meta = data.setdefault("_meta", {})
    meta["last_cleanup"] = _now_local().isoformat(timespec="seconds")

def _migrate_legacy_day(day_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    legacy: { "<uid>": int, ... }
    new:    { "users": { "<uid>": {"text": int, "image": int}, ... } }
    """
    if not isinstance(day_data, dict):
        return {"users": {}}
    if "users" in day_data and isinstance(day_data["users"], dict):
        users = day_data["users"]
        for uid, v in list(users.items()):
            if isinstance(v, int):
                users[uid] = {"text": int(v), "image": 0}
            elif isinstance(v, dict):
                v["text"]  = int(v.get("text") or 0)
                v["image"] = int(v.get("image") or 0)
            else:
                users[uid] = {"text": 0, "image": 0}
        return day_data

    users: Dict[str, Dict[str, int]] = {}
    for k, v in day_data.items():
        if isinstance(v, int):
            users[str(k)] = {"text": int(v), "image": 0}
        elif isinstance(v, dict):
            users[str(k)] = {"text": int(v.get("text") or 0), "image": int(v.get("image") or 0)}
    return {"users": users}

def _load_usage() -> Dict[str, Any]:
    data = _load_json(USAGE_FILE)
    if not isinstance(data, dict):
        data = {}
    return data

def _save_usage(data: Dict[str, Any]) -> None:
    _purge_old_days(data)
    _save_json_atomic(USAGE_FILE, data)

def _ensure_user_bucket(day_bucket: Dict[str, Any], user_id: str) -> Dict[str, int]:
    users = day_bucket.setdefault("users", {})
    if user_id not in users or not isinstance(users[user_id], dict):
        users[user_id] = {"text": 0, "image": 0}
    u = users[user_id]
    u["text"]  = int(u.get("text") or 0)
    u["image"] = int(u.get("image") or 0)
    return u

def _write_legacy_mirrors(day: str, user_id: str, used_text: int, used_image: int) -> None:
    if not WRITE_LEGACY_USAGE_FILES:
        return
    # legacy text
    try:
        u = _load_json(LEGACY_USAGE_FILE)
        u.setdefault(day, {})
        u[day][user_id] = used_text
        _save_json_atomic(LEGACY_USAGE_FILE, u)
    except Exception as e:
        print(f"[context_utils] legacy usage mirror error: {e}")
    # legacy image
    try:
        iu = _load_json(LEGACY_IMAGE_USAGE_FILE)
        iu.setdefault(day, {})
        iu[day][user_id] = used_image
        _save_json_atomic(LEGACY_IMAGE_USAGE_FILE, iu)
    except Exception as e:
        print(f"[context_utils] legacy image mirror error: {e}")

def _limits(is_image: bool, override: Optional[int]=None) -> int:
    if override is not None:
        return int(override)
    return IMAGE_LIMIT_DEFAULT if is_image else TEXT_LIMIT_DEFAULT

# ====================== Public: Usage API ======================
def check_and_increase_usage(
    user_id: str,
    is_image: bool = False,
    limit: Optional[int] = None,
) -> bool:
    """
    ตรวจโควตาวันนี้ แล้วเพิ่มการใช้งาน 1 ครั้งหากยังไม่เกินลิมิต
    True = เพิ่มสำเร็จ / False = เต็มโควตา
    """
    uid = str(user_id)
    if uid in EXEMPT_USER_IDS:
        return True

    day = _today_str()
    with _FileLock(LOCK_FILE):
        data = _load_usage()
        day_bucket = _migrate_legacy_day(data.get(day, {}))
        data[day] = day_bucket
        user_bucket = _ensure_user_bucket(day_bucket, uid)

        key = "image" if is_image else "text"
        lim = _limits(is_image, limit)
        used = int(user_bucket.get(key) or 0)

        if used >= lim:
            return False

        user_bucket[key] = used + 1
        _save_usage(data)

        # mirror legacy counters
        _write_legacy_mirrors(day, uid, int(user_bucket.get("text") or 0), int(user_bucket.get("image") or 0))
        return True

def get_usage_for(
    user_id: str,
    is_image: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, int]:
    """
    คืนค่า {"date": YYYY-MM-DD, "used": N, "limit": L, "remaining": R}
    """
    uid = str(user_id)
    day = _today_str()
    try:
        data = _load_usage()
        day_bucket = _migrate_legacy_day(data.get(day, {}))
        users = day_bucket.get("users", {})
        u = users.get(uid, {"text": 0, "image": 0})
        key = "image" if is_image else "text"
        used = int(u.get(key) or 0)
        lim = _limits(is_image, limit)
        return {"date": day, "used": used, "limit": lim, "remaining": max(lim - used, 0)}
    except Exception:
        lim = _limits(is_image, limit)
        return {"date": day, "used": 0, "limit": lim, "remaining": lim}

def decrease_usage_for(user_id: str, is_image: bool = False, n: int = 1) -> None:
    """ลดตัวนับ (ไม่ต่ำกว่า 0)"""
    if n <= 0:
        return
    uid = str(user_id)
    day = _today_str()
    with _FileLock(LOCK_FILE):
        data = _load_usage()
        day_bucket = _migrate_legacy_day(data.get(day, {}))
        data[day] = day_bucket
        user_bucket = _ensure_user_bucket(day_bucket, uid)
        key = "image" if is_image else "text"
        cur = int(user_bucket.get(key) or 0)
        user_bucket[key] = max(cur - n, 0)
        _save_usage(data)
        _write_legacy_mirrors(day, uid, int(user_bucket.get("text") or 0), int(user_bucket.get("image") or 0))

def reset_usage_for(user_id: Optional[str] = None, date: Optional[str] = None) -> None:
    """
    รีเซ็ตตัวนับ:
      - ระบุ user_id → รีเซ็ตของผู้ใช้นั้นในวัน date (ดีฟอลต์วันนี้)
      - ไม่ระบุ user_id → ลบทั้ง bucket ของวันนั้น
    """
    day = date or _today_str()
    with _FileLock(LOCK_FILE):
        data = _load_usage()
        if user_id is None:
            data.pop(day, None)
        else:
            day_bucket = _migrate_legacy_day(data.get(day, {}))
            users = day_bucket.get("users", {})
            if str(user_id) in users:
                users[str(user_id)] = {"text": 0, "image": 0}
            data[day] = day_bucket
        _save_usage(data)
        # legacy mirrors
        try:
            if WRITE_LEGACY_USAGE_FILES:
                if user_id is None:
                    u = _load_json(LEGACY_USAGE_FILE); u.pop(day, None); _save_json_atomic(LEGACY_USAGE_FILE, u)
                    iu = _load_json(LEGACY_IMAGE_USAGE_FILE); iu.pop(day, None); _save_json_atomic(LEGACY_IMAGE_USAGE_FILE, iu)
                else:
                    u = _load_json(LEGACY_USAGE_FILE); u.setdefault(day, {}); u[day][str(user_id)] = 0; _save_json_atomic(LEGACY_USAGE_FILE, u)
                    iu = _load_json(LEGACY_IMAGE_USAGE_FILE); iu.setdefault(day, {}); iu[day][str(user_id)] = 0; _save_json_atomic(LEGACY_IMAGE_USAGE_FILE, iu)
        except Exception as e:
            print(f"[context_utils] reset legacy mirror error: {e}")

def get_totals_today() -> Dict[str, int]:
    """รวมการใช้งานวันนี้ (ทุกผู้ใช้): {"text": N, "image": M, "users": U}"""
    day = _today_str()
    data = _load_usage()
    day_bucket = _migrate_legacy_day(data.get(day, {}))
    users: Dict[str, Dict[str, int]] = day_bucket.get("users", {})  # type: ignore
    total_text = sum(int(v.get("text") or 0) for v in users.values())
    total_image = sum(int(v.get("image") or 0) for v in users.values())
    return {"text": total_text, "image": total_image, "users": len(users or {})}

# ====================== Context (แบบเก่า: list[str]) ======================
def _as_uid(user_id: Any) -> str:
    return str(user_id)

def get_context(user_id: str) -> List[str]:
    ctx = _load_json(CONTEXT_FILE)
    val = ctx.get(_as_uid(user_id), [])
    if isinstance(val, list):
        out: List[str] = []
        for x in val:
            out.append(x if isinstance(x, str) else str(x))
        return out
    return []

def update_context(user_id: str, text: str, keep_last: int = 6) -> None:
    ctx = _load_json(CONTEXT_FILE)
    uid = _as_uid(user_id)
    ctx.setdefault(uid, [])
    ctx[uid].append(text)
    ctx[uid] = ctx[uid][-keep_last:]
    _save_json_atomic(CONTEXT_FILE, ctx)

def reset_context(user_id: str) -> None:
    ctx = _load_json(CONTEXT_FILE)
    ctx[_as_uid(user_id)] = []
    _save_json_atomic(CONTEXT_FILE, ctx)

def is_waiting_review(user_id: str) -> bool:
    c = get_context(user_id)
    return bool(c and c[-1] == "__wait_review__")

def _extract_last_text(prev_context: List[str] | List[Dict[str, Any]]) -> str:
    if not prev_context:
        return ""
    last = prev_context[-1]
    if isinstance(last, dict):
        return str(last.get("content") or "")
    return str(last)

def should_reset_context(new_text: str, prev_context: list) -> bool:
    if not prev_context:
        return False
    last_text = _extract_last_text(prev_context)
    topics = ["ทอง", "หวย", "อากาศ", "ข่าว", "หุ้น", "น้ำมัน", "สุขภาพ", "ฟุตบอล"]
    if any(t in last_text for t in topics) and not any(t in new_text for t in topics):
        return True
    if new_text.strip().lower() in ["/reset", "เริ่มใหม่", "รีเซ็ต"]:
        return True
    return False

# ====================== Context (แบบใหม่: messages) ======================
def _load_msg_ctx() -> dict:
    return _load_json(CONTEXT_MSG_FILE)

def _save_msg_ctx(data: dict) -> None:
    _save_json_atomic(CONTEXT_MSG_FILE, data)

def get_context_messages(user_id: str) -> List[Dict[str, str]]:
    ctx = _load_msg_ctx()
    val = ctx.get(_as_uid(user_id), [])
    out: List[Dict[str, str]] = []
    if isinstance(val, list):
        for x in val:
            if isinstance(x, dict) and "role" in x and "content" in x:
                role = str(x["role"]).lower().strip()
                content = str(x["content"])
                if role in ("user", "assistant", "system"):
                    out.append({"role": role, "content": content})
    return out

def append_message(user_id: str, role: str, content: str, keep_last: int = 6) -> None:
    role_norm = (role or "").lower().strip()
    if role_norm not in ("user", "assistant", "system"):
        role_norm = "user"
    ctx = _load_msg_ctx()
    uid = _as_uid(user_id)
    ctx.setdefault(uid, [])
    ctx[uid].append({"role": role_norm, "content": content})
    ctx[uid] = ctx[uid][-keep_last:]
    _save_msg_ctx(ctx)

def reset_context_messages(user_id: str) -> None:
    ctx = _load_msg_ctx()
    ctx[_as_uid(user_id)] = []
    _save_msg_ctx(ctx)

def should_reset_context_messages(new_text: str, prev_messages: List[Dict[str, str]]) -> bool:
    last_text = _extract_last_text(prev_messages)
    return should_reset_context(new_text, [last_text] if last_text else [])

def to_recent_llm_messages(user_id: str, keep_last: int = 6) -> List[Dict[str, str]]:
    msgs = get_context_messages(user_id)
    return msgs[-keep_last:]

# ====================== Location ======================
def get_user_location(user_id: str) -> Optional[Dict[str, Any]]:
    loc = _load_json(LOCATION_FILE)
    val = loc.get(_as_uid(user_id))
    if isinstance(val, dict):
        return val
    return None

def get_user_location_coords(user_id: str) -> Optional[Tuple[float, float]]:
    info = get_user_location(user_id)
    if not info:
        return None
    try:
        return float(info["lat"]), float(info["lon"])
    except Exception:
        return None

def update_location(user_id: str, lat: float, lon: float) -> None:
    loc = _load_json(LOCATION_FILE)
    loc[_as_uid(user_id)] = {"lat": float(lat), "lon": float(lon), "ts": _now_local().isoformat(timespec="seconds")}
    _save_json_atomic(LOCATION_FILE, loc)

# alias เพื่อความเข้ากันได้กับโค้ดที่เรียกชื่อเดิม (ถ้ามี)
def update_user_location(user_id: str, lat: float, lon: float) -> None:
    update_location(user_id, lat, lon)
