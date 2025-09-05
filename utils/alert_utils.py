# utils/alert_utils.py
# -*- coding: utf-8 -*-
"""
Alert utilities (safe & throttled)

สิ่งที่เพิ่มจากของเดิม:
- อ่าน log แบบปลอดภัย (ข้ามไฟล์พัง), จำกัดจำนวนรายการล่าสุด
- ตรวจ "ถามซ้ำ" ด้วย threshold และ window ปรับได้ผ่าน ENV
- ตรวจ "ปริมาณพุ่ง" (usage spike) แบบง่ายใน 10 นาทีล่าสุด (ปรับได้)
- กันสแปมด้วย throttle/cooldown ต่อเหตุการณ์ (บันทึกใน data/alert_state.json)
- ส่งไม่ได้ (ไม่มี ADMIN_CHAT_ID) จะ log ไว้ แต่ไม่พัง

ENV:
  ADMIN_CHAT_ID                      = chat_id ผู้ดูแล
  ALERT_HISTORY_DIR                  = โฟลเดอร์ log (default: chat_logs)
  ALERT_LAST_STATE_FILE              = path state throttle (default: data/alert_state.json)
  ALERT_WINDOW_LAST_N                = ขอบเขต log ล่าสุดที่พิจารณา (default: 200)
  ALERT_REPEAT_THRESHOLD             = นับ "คำถามเดียวกัน" ถึงกี่ครั้งภายใน window (default: 4)
  ALERT_USAGE_WINDOW_MIN             = นาทีที่ใช้วัดปริมาณล่าสุด (default: 10)
  ALERT_USAGE_THRESHOLD              = เกณฑ์จำนวนรายการภายในหน้าต่าง (default: 40)
  ALERT_COOLDOWN_MIN                 = นาทีพักต่อเหตุการณ์ (default: 30)
  ALERT_MAX_PER_RUN                  = จำกัดจำนวน alert ต่อการรันหนึ่งครั้ง (default: 5)

รูปแบบ log ที่รองรับ (ยืดหยุ่น):
  - ไฟล์ JSON array ของ record เช่น {"q": "...", "ts": "...", "user_id": "..."}
  - ถ้าไม่มี ts จะถือเป็นล่าสุดสุดท้ายตามลำดับไฟล์/รายการ
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import os
import json
import time
import hashlib
from datetime import datetime, timedelta

# ส่งข้อความ (ต้องมีฟังก์ชันนี้ตามระบบเดิม)
from utils.message_utils import send_message

# I/O ปลอดภัย (ถ้ามี)
try:
    from utils.json_utils import load_json_safe as _load_json_safe, save_json_safe as _save_json_safe
except Exception:
    _load_json_safe = None
    _save_json_safe = None

# ------------------ Config ------------------
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # ใส่ chat_id แอดมิน

HISTORY_DIR            = os.getenv("ALERT_HISTORY_DIR", "chat_logs")
STATE_FILE             = os.getenv("ALERT_LAST_STATE_FILE", "data/alert_state.json")

WINDOW_LAST_N          = int(os.getenv("ALERT_WINDOW_LAST_N", "200"))
REPEAT_THRESHOLD       = int(os.getenv("ALERT_REPEAT_THRESHOLD", "4"))   # เดิม: เกิน 3 → แจ้งตอนครั้งที่ 4
USAGE_WINDOW_MIN       = int(os.getenv("ALERT_USAGE_WINDOW_MIN", "10"))
USAGE_THRESHOLD        = int(os.getenv("ALERT_USAGE_THRESHOLD", "40"))

COOLDOWN_MIN           = int(os.getenv("ALERT_COOLDOWN_MIN", "30"))
ALERT_MAX_PER_RUN      = int(os.getenv("ALERT_MAX_PER_RUN", "5"))

# ------------------ Helpers ------------------
def _now() -> datetime:
    return datetime.now()

def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _read_state() -> Dict[str, Any]:
    try:
        if _load_json_safe:
            return _load_json_safe(STATE_FILE, default={})
        if not os.path.exists(STATE_FILE):
            return {}
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_state(data: Dict[str, Any]) -> None:
    try:
        _ensure_dir(STATE_FILE)
        if _save_json_safe:
            _save_json_safe(data, STATE_FILE, ensure_ascii=False, indent=2, sort_keys=False)
            return
        tmp = f"{STATE_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        print(f"[alert_utils] write_state error: {e}")

def _norm_question(q: str) -> str:
    q = (q or "").strip().lower()
    # ตัดเว้นวรรคซ้ำ, ตัดจุดท้ายยาว ๆ เพื่อ normalize เบื้องต้น
    q = " ".join(q.split())
    return q

def _hash_key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]

def _should_send_throttled(state: Dict[str, Any], key: str, cooldown_min: int) -> bool:
    last = state.get("last_sent", {}).get(key)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True
    return (_now() - last_dt) >= timedelta(minutes=cooldown_min)

def _mark_sent(state: Dict[str, Any], key: str) -> None:
    state.setdefault("last_sent", {})[key] = _now().isoformat(timespec="seconds")

def _safe_listdir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except Exception:
        return []

def _load_logs_from_dir(history_dir: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not os.path.exists(history_dir):
        return records
    for fname in _safe_listdir(history_dir):
        fpath = os.path.join(history_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for it in data:
                    if isinstance(it, dict):
                        records.append(it)
        except Exception:
            continue
    # เอาเฉพาะท้าย ๆ ตาม window
    return records[-max(10, WINDOW_LAST_N):]

def _extract_ts(rec: Dict[str, Any]) -> Optional[datetime]:
    # รองรับ key ts/timestamp หรือไม่มีเลย
    for k in ("ts", "timestamp", "time"):
        v = rec.get(k)
        if not v:
            continue
        # รองรับรูปแบบ ISO / epoch (วินาที/มิลลิวินาที)
        if isinstance(v, (int, float)):
            # เดาว่า >= 10^12 = ms
            try:
                if v > 1e11:
                    return datetime.fromtimestamp(v / 1000.0)
                return datetime.fromtimestamp(v)
            except Exception:
                continue
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                # ลอง parse แบบง่าย ๆ: "YYYY-MM-DD HH:MM:SS"
                try:
                    return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
    return None  # ไม่มี ts ก็ให้ไปจัดเรียงตามลำดับที่อ่าน

# ------------------ Analyzers ------------------
def _analyze_repeats(logs: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    """
    คืนรายการ [(question_norm, count)] ที่ถึง threshold
    """
    from collections import Counter
    ctr = Counter()
    for rec in logs:
        q = _norm_question(rec.get("q", ""))
        if q:
            ctr[q] += 1
    # คัดเฉพาะที่ถึง threshold
    results = [(q, c) for q, c in ctr.most_common() if c >= REPEAT_THRESHOLD]
    return results

def _analyze_usage_spike(logs: List[Dict[str, Any]]) -> int:
    """
    นับจำนวนรายการในหน้าต่างเวลา USAGE_WINDOW_MIN ล่าสุด
    ถ้าไม่มี timestamp จะถือเป็นรายการล่าสุดทั้งหมด
    """
    if not logs:
        return 0
    # ลองใช้ timestamp ถ้ามี
    now = _now()
    window_start = now - timedelta(minutes=USAGE_WINDOW_MIN)

    # ถ้าไม่มี ts เลย ก็ให้ใช้เพียงสัดส่วนรายการท้าย ๆ
    any_ts = any(_extract_ts(r) for r in logs)
    if not any_ts:
        return len(logs)  # ประเมินหยาบ ๆ ที่ window ปัจจุบัน

    count = 0
    for r in logs:
        ts = _extract_ts(r)
        if not ts:
            # ถ้า record นี้ไม่มี ts ให้ถือว่าอยู่ใน window เพื่อไม่พลาดการเตือน
            count += 1
        elif ts >= window_start:
            count += 1
    return count

# ------------------ Sender ------------------
def _send_admin(text: str) -> None:
    if not ADMIN_CHAT_ID:
        print("[alert_utils] ADMIN_CHAT_ID not set, message suppressed:", text)
        return
    try:
        send_message(ADMIN_CHAT_ID, text)
    except Exception as e:
        print(f"[alert_utils] send_message error: {e} | msg={text}")

# ------------------ Main entry ------------------
def check_and_alert():
    """
    ตรวจ log และแจ้งเตือนแอดมินเมื่อพบ:
      1) คำถามซ้ำผิดปกติ (ถึง threshold ใน window ล่าสุด)
      2) ปริมาณการใช้งานพุ่งใน {USAGE_WINDOW_MIN} นาทีล่าสุด (>= USAGE_THRESHOLD)
    ใช้ throttle ป้องกันการแจ้งซ้ำในช่วง {COOLDOWN_MIN} นาที
    """
    logs = _load_logs_from_dir(HISTORY_DIR)
    state = _read_state()
    alerts_sent = 0

    # 1) ซ้ำผิดปกติ (top hits)
    repeats = _analyze_repeats(logs)
    for q_norm, count in repeats[:3]:  # แจ้ง top 3
        key = f"repeat:{_hash_key(q_norm)}"
        if not _should_send_throttled(state, key, COOLDOWN_MIN):
            continue
        _send_admin(f"⚠️ พบการถามซ้ำบ่อย: “{q_norm}” ในหน้าต่างล่าสุด {count} ครั้ง")
        _mark_sent(state, key)
        alerts_sent += 1
        if alerts_sent >= ALERT_MAX_PER_RUN:
            break

    # 2) ปริมาณพุ่ง
    if alerts_sent < ALERT_MAX_PER_RUN:
        usage_count = _analyze_usage_spike(logs)
        if usage_count >= USAGE_THRESHOLD:
            key = f"volume:{USAGE_WINDOW_MIN}m:{USAGE_THRESHOLD}"
            if _should_send_throttled(state, key, COOLDOWN_MIN):
                _send_admin(f"📈 ปริมาณคำถามพุ่ง: {usage_count} รายการใน {USAGE_WINDOW_MIN} นาทีล่าสุด")
                _mark_sent(state, key)
                alerts_sent += 1

    # บันทึก state (throttle)
    _write_state(state)
    return {"checked": True, "alerts_sent": alerts_sent}
