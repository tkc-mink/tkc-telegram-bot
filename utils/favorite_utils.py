# utils/favorite_utils.py
# -*- coding: utf-8 -*-
"""
เครื่องมือจัดการ 'รายการโปรด' ของผู้ใช้
- จัดเก็บในไฟล์ JSON เดียว: data/favorites.json
- โครงสร้าง: { "<user_id>": [ { "text": "...", "q": "...", "date": "YYYY-MM-DD HH:MM" }, ... ] }
- รองรับ:
    add_favorite(user_id, text)                   -> bool
    get_favorites(user_id, limit=10)              -> list[dict]
    remove_favorite(user_id, index=None, text=None) -> bool
หมายเหตุ:
- index เป็นลำดับแบบ 1-based ของรายการที่ "เรียงใหม่จากล่าสุดไปเก่าสุด"
- ลบตามข้อความ: เทียบแบบ case-insensitive หลัง trim ช่องว่าง
"""

from __future__ import annotations
import os
import json
import threading
from typing import Dict, List, Optional
from datetime import datetime

# ---- Timezone helper (Asia/Bangkok ถ้ามี tzdata/pytz) ----
def _now_str() -> str:
    try:
        import pytz  # type: ignore
        tz = pytz.timezone("Asia/Bangkok")
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

# ---- Storage paths ----
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # project root/utils -> project root
DATA_DIR = os.path.join(BASE_DIR, "data")
FAV_FILE = os.path.join(DATA_DIR, "favorites.json")

# ---- In-process lock (กัน race ภายในโปรเซสเดียว) ----
_LOCK = threading.Lock()


def _ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(FAV_FILE):
        with open(FAV_FILE, "w", encoding="utf-8") as f:
            f.write("{}")  # empty dict


def _load_db() -> Dict[str, List[Dict]]:
    _ensure_dirs()
    try:
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _atomic_write(data: Dict) -> None:
    tmp = FAV_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FAV_FILE)


def _normalize_text(s: str) -> str:
    return (s or "").strip()


def _key_for_compare(s: str) -> str:
    # ใช้สำหรับเทียบความซ้ำ: ไม่สนช่องว่างหัวท้าย + ตัวพิมพ์เล็ก
    return _normalize_text(s).lower()


def add_favorite(user_id: str | int, text: str) -> bool:
    """
    เพิ่มรายการโปรดให้ผู้ใช้ (กันซ้ำแบบ case-insensitive)
    :return: True ถ้าเพิ่มได้, False ถ้าซ้ำ/ไม่สามารถเพิ่ม
    """
    uid = str(user_id)
    t = _normalize_text(text)
    if not t:
        return False

    with _LOCK:
        db = _load_db()
        items: List[Dict] = db.get(uid, [])

        # กันซ้ำ
        exists = any(_key_for_compare(x.get("text") or x.get("q") or "") == _key_for_compare(t) for x in items)
        if exists:
            return False

        entry = {"text": t, "q": t, "date": _now_str()}
        items.append(entry)
        db[uid] = items
        _atomic_write(db)
        return True


def get_favorites(user_id: str | int, limit: int = 10) -> List[Dict]:
    """
    คืนรายการโปรดของผู้ใช้ เรียงจาก 'ล่าสุด -> เก่าสุด'
    """
    uid = str(user_id)
    with _LOCK:
        db = _load_db()
        items: List[Dict] = db.get(uid, [])

        # เรียงใหม่: ล่าสุดก่อน (date ใหม่อยู่ท้าย list เดิมเพราะ append)
        items_sorted = list(reversed(items))
        if limit and limit > 0:
            items_sorted = items_sorted[:limit]
        return items_sorted


def remove_favorite(
    user_id: str | int,
    index: Optional[int] = None,
    text: Optional[str] = None
) -> bool:
    """
    ลบรายการโปรดตาม 'index' (1-based, อิงจากลิสต์ที่เรียงใหม่ล่าสุดก่อน)
    หรือ 'text' (เทียบแบบ case-insensitive)
    :return: True ถ้าลบสำเร็จอย่างน้อย 1 รายการ
    """
    uid = str(user_id)

    if index is None and not text:
        return False

    with _LOCK:
        db = _load_db()
        items: List[Dict] = db.get(uid, [])
        if not items:
            return False

        changed = False

        if index is not None:
            # แปลงเป็นลำดับในรายการเดิม (ซึ่งเก็บแบบเก่าสุดอยู่ต้นลิสต์)
            # ปัจจุบันเรานิยาม index จาก "รายการเรียงล่าสุดก่อน"
            # items_old = [oldest,..., newest]
            # items_sorted = [newest,..., oldest]
            # ดังนั้น index 1 => newest => ตำแหน่ง len(items)-1
            if index <= 0 or index > len(items):
                return False
            pos = len(items) - index  # แปลงกลับไป index ใน items เดิม
            if 0 <= pos < len(items):
                del items[pos]
                changed = True

        elif text is not None:
            key = _key_for_compare(text)
            new_items = [x for x in items if _key_for_compare(x.get("text") or x.get("q") or "") != key]
            if len(new_items) != len(items):
                db[uid] = new_items
                changed = True
                items = new_items  # update local reference

        if changed:
            db[uid] = items
            _atomic_write(db)
        return changed
