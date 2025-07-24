import os
import json
from datetime import datetime

FAV_FILE = "data/favorites.json"

def _load_data():
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_data(data):
    os.makedirs(os.path.dirname(FAV_FILE), exist_ok=True)
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_favorite(user_id, question: str) -> bool:
    """
    เพิ่มคำถามโปรด ถ้ายังไม่มี (ป้องกันซ้ำ)
    คืนค่า True = เพิ่มสำเร็จ, False = มีซ้ำอยู่แล้ว
    """
    question = question.strip()[:120]  # limit length
    if not question:
        return False
    data = _load_data()
    key = str(user_id)
    favs = data.get(key, [])
    if any(item["q"] == question for item in favs):
        return False
    favs.append({
        "q": question,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    data[key] = favs
    _save_data(data)
    return True

def get_favorites(user_id, limit=10):
    """
    คืนค่ารายการโปรดย้อนหลัง (สูงสุด limit รายการล่าสุด)
    """
    data = _load_data()
    favs = data.get(str(user_id), [])
    return favs[-limit:]

def remove_favorite(user_id, question: str) -> bool:
    """
    ลบคำถามโปรดตามข้อความ
    คืนค่า True = ลบสำเร็จ, False = ไม่มีในรายการ
    """
    question = question.strip()[:120]
    data = _load_data()
    key = str(user_id)
    favs = data.get(key, [])
    new_favs = [item for item in favs if item["q"] != question]
    if len(new_favs) == len(favs):
        return False
    data[key] = new_favs
    _save_data(data)
    return True
