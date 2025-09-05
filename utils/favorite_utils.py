# utils/favorite_utils.py
# -*- coding: utf-8 -*-
"""
Utility functions for handling user favorites.
Acts as a clean, hardened interface to the persistent database (memory_store).
- Validate & sanitize inputs
- Avoid over-fetching
- Helpful extras for common UI flows
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

from utils.memory_store import (
    add_favorite,
    get_favorites_by_user,
    remove_favorite_by_id,
)

# memory_store._norm_text cap คือ ~4000 ตัวอักษร
_FAVORITE_MAX_LEN = 4000


def _sanitize_content(content: Optional[str]) -> Optional[str]:
    """
    ตัดช่องว่าง/บรรทัดเกิน, กันค่าว่าง, จำกัดความยาวให้สอดคล้อง memory_store
    """
    if content is None:
        return None
    # collapse whitespace
    s = " ".join(str(content).split()).strip()
    if not s:
        return None
    if len(s) > _FAVORITE_MAX_LEN:
        s = s[:_FAVORITE_MAX_LEN]
    return s


def add_new_favorite(user_id: int, content: str) -> bool:
    """
    บันทึกรายการโปรดใหม่ของผู้ใช้ลงในฐานข้อมูล (drop-in)
    - กันค่าว่าง/ความยาวเกินก่อนส่งเข้า memory_store
    """
    try:
        cleaned = _sanitize_content(content)
        if not cleaned:
            print(f"[Favorite_Utils] Reject empty/invalid favorite for user {user_id}")
            return False
        ok = add_favorite(user_id, cleaned)
        if not ok:
            print(f"[Favorite_Utils] add_favorite returned False for user {user_id}")
        return ok
    except Exception as e:
        print(f"[Favorite_Utils] add_new_favorite error: {e}")
        return False


def get_user_favorites(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    ดึงรายการโปรดล่าสุดของผู้ใช้จากฐานข้อมูล (drop-in)
    - บังคับ limit ขั้นต่ำ 1 ป้องกันเคสพลาด
    """
    try:
        lim = max(1, int(limit or 10))
    except Exception:
        lim = 10
    try:
        favs = get_favorites_by_user(user_id, lim) or []
        # คงรูปแบบเดิม: list[ dict(favorite_id, content) ]
        return favs
    except Exception as e:
        print(f"[Favorite_Utils] get_user_favorites error: {e}")
        return []


def remove_user_favorite(user_id: int, index: int) -> bool:
    """
    ลบรายการโปรดตามลำดับที่แสดง (1-based)
    - ดึงมาเท่าที่จำเป็น (อย่างน้อย index รายการ) แทนการดึง 100 เสมอ
    """
    try:
        idx = int(index)
    except Exception:
        print(f"[Favorite_Utils] Invalid index type: {index!r}")
        return False

    if idx < 1:
        print(f"[Favorite_Utils] Index {idx} must be >= 1")
        return False

    # ดึงมาให้ครอบคลุมลำดับที่ต้องการ (ลด over-fetch)
    fetch_limit = max(10, idx)
    try:
        favorites = get_favorites_by_user(user_id, limit=fetch_limit) or []
    except Exception as e:
        print(f"[Favorite_Utils] fetch favorites error: {e}")
        return False

    if idx > len(favorites):
        print(f"[Favorite_Utils] Index {idx} out of bounds (size={len(favorites)})")
        return False

    fav = favorites[idx - 1]
    fav_id = fav.get("favorite_id")
    if not isinstance(fav_id, int):
        try:
            fav_id = int(fav_id)
        except Exception:
            print(f"[Favorite_Utils] Invalid favorite_id at index {idx}: {fav_id!r}")
            return False

    print(f"[Favorite_Utils] Deleting favorite_id={fav_id} for user {user_id}")
    try:
        return remove_favorite_by_id(fav_id, user_id)
    except Exception as e:
        print(f"[Favorite_Utils] remove_favorite_by_id error: {e}")
        return False


# -------- Optional helpers (ไม่บังคับใช้ แต่มีประโยชน์) --------
def remove_user_favorite_by_id(user_id: int, favorite_id: int) -> bool:
    """
    ลบโดยใช้ favorite_id ตรง ๆ (เผื่อ UI เก็บไอดีไว้แล้ว)
    """
    try:
        fid = int(favorite_id)
    except Exception:
        print(f"[Favorite_Utils] Invalid favorite_id: {favorite_id!r}")
        return False
    try:
        return remove_favorite_by_id(fid, user_id)
    except Exception as e:
        print(f"[Favorite_Utils] remove_user_favorite_by_id error: {e}")
        return False


def list_user_favorites_text(user_id: int, limit: int = 10) -> str:
    """
    จัดรูปข้อความรายการโปรดสำหรับแสดงผล (เช่นในแช็ต)
    1) <content A>
    2) <content B>
    """
    favs = get_user_favorites(user_id, limit=limit)
    if not favs:
        return "ยังไม่มีรายการโปรด"
    lines = []
    for i, it in enumerate(favs, 1):
        txt = str(it.get("content", "")).strip()
        lines.append(f"{i}) {txt}" if txt else f"{i}) (ว่าง)")
    return "\n".join(lines)
