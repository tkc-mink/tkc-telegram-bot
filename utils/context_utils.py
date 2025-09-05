# utils/context_utils.py
# -*- coding: utf-8 -*-
"""
จัดการ context / usage / location สำหรับผู้ใช้
- Backward-compatible กับเวอร์ชันเดิม (context แบบ list[str])
- เพิ่มระบบ context แบบ message (list[{"role","content"}]) แยกไฟล์ เพื่อใช้กับ LLM/Orchestrator
- Atomic JSON write ลดโอกาสไฟล์เสียเมื่อเขียนพร้อมกัน
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json
import os
from datetime import datetime

# ====== ไฟล์เก็บข้อมูล (เก่า) ======
USAGE_FILE        = os.getenv("USAGE_FILE", "usage.json")
IMAGE_USAGE_FILE  = os.getenv("IMAGE_USAGE_FILE", "image_usage.json")
CONTEXT_FILE      = os.getenv("CONTEXT_FILE", "context_history.json")  # list[str] แบบเดิม
LOCATION_FILE     = os.getenv("LOCATION_FILE", "location_logs.json")

# ====== ไฟล์เก็บข้อมูล (ใหม่: context แบบ message) ======
CONTEXT_MSG_FILE  = os.getenv("CONTEXT_MSG_FILE", "context_messages.json")  # list[{"role","content"}]

# ====== ค่า limit ======
MAX_QUESTION_PER_DAY = int(os.getenv("MAX_QUESTION_PER_DAY", 30))
MAX_IMAGE_PER_DAY    = int(os.getenv("MAX_IMAGE_PER_DAY", 15))

# แปลง EXEMPT_USER_IDS เป็น set ของ string (ตัดช่องว่าง/ค่าว่าง)
_exempt_raw = os.getenv("EXEMPT_USER_IDS", "6849909227")
EXEMPT_USER_IDS: set[str] = {x.strip() for x in _exempt_raw.split(",") if x.strip()}

# ---------------- JSON helpers ----------------
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
    """
    เขียนไฟล์แบบ atomic: เขียนลง .tmp ก่อน แล้วค่อย os.replace เป็นไฟล์จริง
    (ลดความเสี่ยงไฟล์พังหากเขียนพร้อมกัน)
    """
    try:
        _ensure_parent_dir(path)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print(f"[context_utils] save_json_atomic({path}) error: {e}")

# ---------------- Usage Counter ----------------
def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _as_uid(user_id: Any) -> str:
    return str(user_id)

def _check_and_increase_generic(file_path: str, limit: int, user_id: str, when: Optional[str] = None) -> bool:
    """
    true = ยังเหลือสิทธิ์, false = เกิน limit แล้ว
    """
    uid = _as_uid(user_id)
    if uid in EXEMPT_USER_IDS:
        return True

    day = when or _today_str()
    usage = _load_json(file_path)
    usage.setdefault(day, {})
    usage[day].setdefault(uid, 0)

    if usage[day][uid] >= limit:
        return False

    usage[day][uid] += 1
    _save_json_atomic(file_path, usage)
    return True

def check_and_increase_usage(user_id: str, is_image: bool = False) -> bool:
    """
    true = ยังเหลือสิทธิ์, false = เกิน limit แล้ว (คง signature เดิม)
    """
    if is_image:
        return _check_and_increase_generic(IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY, user_id)
    return _check_and_increase_generic(USAGE_FILE, MAX_QUESTION_PER_DAY, user_id)

def get_usage_for(user_id: str, is_image: bool = False) -> Dict[str, int]:
    """
    คืนค่า {"used": N, "limit": L, "remaining": R} สำหรับวันนี้
    """
    uid = _as_uid(user_id)
    day = _today_str()
    file_path = IMAGE_USAGE_FILE if is_image else USAGE_FILE
    limit     = MAX_IMAGE_PER_DAY if is_image else MAX_QUESTION_PER_DAY

    usage = _load_json(file_path)
    used = usage.get(day, {}).get(uid, 0)
    rem = max(0, limit - used)
    return {"used": used, "limit": limit, "remaining": rem}

def remaining_quota(user_id: str) -> Tuple[int, int]:
    """
    คืนค่า (remaining_questions, remaining_images) สำหรับวันนี้
    """
    q = get_usage_for(user_id, is_image=False)["remaining"]
    i = get_usage_for(user_id, is_image=True)["remaining"]
    return (q, i)

# ---------------- Context (แบบเก่า: list[str]) ----------------
def get_context(user_id: str) -> List[str]:
    ctx = _load_json(CONTEXT_FILE)
    val = ctx.get(_as_uid(user_id), [])
    # ยืนยันชนิดเป็น list[str]
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
    """
    รองรับทั้ง context เก่า (list[str]) และแบบใหม่ (list[dict[role,content]])
    คืนค่าข้อความล่าสุด (content)
    """
    if not prev_context:
        return ""
    last = prev_context[-1]
    if isinstance(last, dict):
        return str(last.get("content") or "")
    return str(last)

def should_reset_context(new_text: str, prev_context: list) -> bool:
    """
    กติกาเดิม + รองรับโครงสร้างแบบข้อความ (dict)
    """
    if not prev_context:
        return False
    last_text = _extract_last_text(prev_context)
    topics = ["ทอง", "หวย", "อากาศ", "ข่าว", "หุ้น", "น้ำมัน", "สุขภาพ", "ฟุตบอล"]
    if any(t in last_text for t in topics) and not any(t in new_text for t in topics):
        return True
    if new_text.strip().lower() in ["/reset", "เริ่มใหม่", "รีเซ็ต"]:
        return True
    return False

# ---------------- Context (แบบใหม่: list[{"role","content"}]) ----------------
def _load_msg_ctx() -> dict:
    return _load_json(CONTEXT_MSG_FILE)

def _save_msg_ctx(data: dict) -> None:
    _save_json_atomic(CONTEXT_MSG_FILE, data)

def get_context_messages(user_id: str) -> List[Dict[str, str]]:
    """
    คืนค่า list ของ messages: [{"role":"user"/"assistant", "content":"..."}]
    ถ้าไฟล์ยังไม่มี จะคืนเป็นลิสต์ว่าง
    """
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
    """
    เพิ่มข้อความแบบ message context (ใหม่)
    """
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
    """
    เงื่อนไขคล้ายของเดิม แต่ทำงานกับ message objects
    """
    last_text = _extract_last_text(prev_messages)
    return should_reset_context(new_text, [last_text] if last_text else [])

def to_recent_llm_messages(user_id: str, keep_last: int = 6) -> List[Dict[str, str]]:
    """
    ดึง messages ล่าสุด (role/content) สำหรับ LLM/Orchestrator
    """
    msgs = get_context_messages(user_id)
    return msgs[-keep_last:]

# ---------------- Location ----------------
def get_user_location(user_id: str) -> Optional[Dict[str, Any]]:
    loc = _load_json(LOCATION_FILE)
    val = loc.get(_as_uid(user_id))
    if isinstance(val, dict):
        return val
    return None

def get_user_location_coords(user_id: str) -> Optional[Tuple[float, float]]:
    """
    คืน (lat, lon) ถ้ามีข้อมูล มิฉะนั้นคืน None
    """
    info = get_user_location(user_id)
    if not info:
        return None
    try:
        return float(info["lat"]), float(info["lon"])
    except Exception:
        return None

def update_location(user_id: str, lat: float, lon: float) -> None:
    loc = _load_json(LOCATION_FILE)
    loc[_as_uid(user_id)] = {"lat": float(lat), "lon": float(lon), "ts": datetime.now().isoformat()}
    _save_json_atomic(LOCATION_FILE, loc)
