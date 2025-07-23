# utils/context_utils.py
"""
จัดการ context / usage / location สำหรับผู้ใช้
"""

import json
import os
from datetime import datetime

# ====== ไฟล์เก็บข้อมูล ======
USAGE_FILE        = os.getenv("USAGE_FILE", "usage.json")
IMAGE_USAGE_FILE  = os.getenv("IMAGE_USAGE_FILE", "image_usage.json")
CONTEXT_FILE      = os.getenv("CONTEXT_FILE", "context_history.json")
LOCATION_FILE     = os.getenv("LOCATION_FILE", "location_logs.json")

# ====== ค่า limit ======
MAX_QUESTION_PER_DAY = int(os.getenv("MAX_QUESTION_PER_DAY", 30))
MAX_IMAGE_PER_DAY    = int(os.getenv("MAX_IMAGE_PER_DAY", 15))
EXEMPT_USER_IDS      = os.getenv("EXEMPT_USER_IDS", "6849909227").split(",")

# ---------------- JSON helper ----------------
def _load_json(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[context_utils] load_json({path}) error: {e}")
        return {}

def _save_json(path: str, data: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils] save_json({path}) error: {e}")

# ---------------- Usage Counter ----------------
def check_and_increase_usage(user_id: str, is_image: bool = False) -> bool:
    """
    true = ยังเหลือสิทธิ์, false = เกิน limit แล้ว
    """
    if user_id in EXEMPT_USER_IDS:
        return True

    file_path = IMAGE_USAGE_FILE if is_image else USAGE_FILE
    limit     = MAX_IMAGE_PER_DAY if is_image else MAX_QUESTION_PER_DAY

    today = datetime.now().strftime("%Y-%m-%d")
    usage = _load_json(file_path)
    usage.setdefault(today, {})
    usage[today].setdefault(user_id, 0)

    if usage[today][user_id] >= limit:
        return False

    usage[today][user_id] += 1
    _save_json(file_path, usage)
    return True

# ---------------- Context ----------------
def get_context(user_id: str):
    ctx = _load_json(CONTEXT_FILE)
    return ctx.get(user_id, [])

def update_context(user_id: str, text: str, keep_last: int = 6):
    ctx = _load_json(CONTEXT_FILE)
    ctx.setdefault(user_id, []).append(text)
    ctx[user_id] = ctx[user_id][-keep_last:]
    _save_json(CONTEXT_FILE, ctx)

def reset_context(user_id: str):
    ctx = _load_json(CONTEXT_FILE)
    ctx[user_id] = []
    _save_json(CONTEXT_FILE, ctx)

def is_waiting_review(user_id: str) -> bool:
    c = get_context(user_id)
    return bool(c and c[-1] == "__wait_review__")

def should_reset_context(new_text: str, prev_context: list) -> bool:
    if not prev_context:
        return False
    last = prev_context[-1] if prev_context else ""
    topics = ["ทอง", "หวย", "อากาศ", "ข่าว", "หุ้น", "น้ำมัน", "สุขภาพ", "ฟุตบอล"]
    if any(t in last for t in topics) and not any(t in new_text for t in topics):
        return True
    if new_text.strip().lower() in ["/reset", "เริ่มใหม่", "รีเซ็ต"]:
        return True
    return False

# ---------------- Location ----------------
def get_user_location(user_id: str):
    loc = _load_json(LOCATION_FILE)
    return loc.get(user_id)

def update_location(user_id: str, lat: float, lon: float):
    loc = _load_json(LOCATION_FILE)
    loc[user_id] = {"lat": lat, "lon": lon, "ts": datetime.now().isoformat()}
    _save_json(LOCATION_FILE, loc)
