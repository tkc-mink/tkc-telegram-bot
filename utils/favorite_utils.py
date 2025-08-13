# utils/favorite_utils.py
# -*- coding: utf-8 -*-
"""
Utility functions for handling user favorites.
This version acts as a clean interface to the persistent database (memory_store).
"""
from __future__ import annotations
from typing import List, Dict, Optional

# --- ✅ ส่วนที่เราแก้ไข ---
# 1. เปลี่ยนไป import ฟังก์ชันจาก memory_store ที่เราสร้างขึ้น
from utils.memory_store import add_favorite, get_favorites_by_user, remove_favorite_by_id

def add_new_favorite(user_id: int, content: str) -> bool:
    """
    บันทึกรายการโปรดใหม่ของผู้ใช้ลงในฐานข้อมูล
    """
    print(f"[Favorite_Utils] Adding favorite for user {user_id}")
    # ส่งต่อให้ memory_store จัดการการบันทึก
    return add_favorite(user_id, (content or "").strip())

def get_user_favorites(user_id: int, limit: int = 10) -> List[Dict]:
    """
    ดึงรายการโปรดล่าสุดของผู้ใช้จากฐานข้อมูล
    """
    print(f"[Favorite_Utils] Getting favorites for user {user_id}")
    # ส่งต่อให้ memory_store จัดการการดึงข้อมูล
    return get_favorites_by_user(user_id, limit)

def remove_user_favorite(user_id: int, index: int) -> bool:
    """
    ลบรายการโปรดตามลำดับที่แสดงให้ผู้ใช้เห็น (เช่น 1, 2, 3)
    โดยแปลง index ที่ผู้ใช้เห็น เป็น favorite_id จริงในฐานข้อมูล
    """
    print(f"[Favorite_Utils] Attempting to remove favorite at index {index} for user {user_id}")
    
    # 2. ตรรกะที่สำคัญ: เราต้องดึงรายการโปรดทั้งหมดก่อน เพื่อหา ID ที่แท้จริง
    #    ที่เราต้องการลบตามลำดับที่ผู้ใช้เห็น
    favorites = get_favorites_by_user(user_id, limit=100) # ดึงมาเผื่อไว้เยอะๆ
    
    # ตรวจสอบว่าลำดับที่ผู้ใช้ส่งมาถูกต้องหรือไม่
    if not 1 <= index <= len(favorites):
        print(f"[Favorite_Utils] Index {index} is out of bounds.")
        return False

    # ลำดับที่ผู้ใช้เห็นคือ 1, 2, 3 แต่ใน list ของ Python คือ 0, 1, 2
    # เราจึงต้อง -1 เพื่อหาตำแหน่งที่ถูกต้องใน list
    target_favorite_id = favorites[index - 1]['favorite_id']
    
    print(f"[Favorite_Utils] Index {index} corresponds to favorite_id {target_favorite_id}. Deleting...")
    
    # 3. ส่ง ID ที่แท้จริงไปให้ memory_store เพื่อทำการลบ
    return remove_favorite_by_id(target_favorite_id, user_id)
