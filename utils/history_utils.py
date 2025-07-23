# utils/history_utils.py  (ย้ายมาไว้ใต้ utils/ ตามโครงสร้างใหม่)
import os
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Any

# ---- CONFIG ----
HISTORY_FILE = os.getenv("HISTORY_FILE", "data/history.json")
MAX_RECORDS_PER_USER = int(os.getenv("MAX_HISTORY_PER_USER", "100"))

# ใช้ตัวแปร global lock แบบง่ายๆ กันเขียนพร้อมกันหลายครั้งใน process เดียว
from threading import RLock
_LOCK = RLock()


# ---------- Low level helpers ----------
def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

def _atomic_write_json(data: Any, path: str) -> None:
    """เขียนไฟล์แบบ atomic เพื่อลดโอกาสไฟล์พัง"""
    _ensure_parent_dir(path)
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp", prefix="hist_", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


# ---------- Public APIs ----------
def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """โหลดประวัติทั้งหมด (dict[user_id] = list[record])"""
    with _LOCK:
        try:
            if not os.path.exists(HISTORY_FILE):
                return {}
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[history_utils.load_history] {e}")
            return {}

def save_history(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """บันทึกประวัติทั้งหมด"""
    with _LOCK:
        try:
            _atomic_write_json(data, HISTORY_FILE)
        except Exception as e:
            print(f"[history_utils.save_history] {e}")

def log_message(user_id: str, question: str, answer: str) -> None:
    """
    บันทึก Q/A ของผู้ใช้ 1 รายการ
    - เก็บได้สูงสุด MAX_RECORDS_PER_USER รายการล่าสุด
    """
    with _LOCK:
        data = load_history()
        records = data.setdefault(str(user_id), [])
        records.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "q": question,
            "a": answer
        })
        data[str(user_id)] = records[-MAX_RECORDS_PER_USER:]
        save_history(data)

def get_user_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """ดึงประวัติของผู้ใช้ (ล่าสุดก่อน)"""
    data = load_history()
    history = data.get(str(user_id), [])
    return history[-limit:]

# ------- Optional helper functions -------
def clear_user_history(user_id: str) -> None:
    """ลบประวัติของ user คนเดียว"""
    with _LOCK:
        data = load_history()
        if str(user_id) in data:
            del data[str(user_id)]
            save_history(data)

def export_all_history() -> Dict[str, List[Dict[str, Any]]]:
    """คืนค่าประวัติทั้งหมด (สำหรับ backup/export)"""
    return load_history()
