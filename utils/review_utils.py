import json
from datetime import datetime, timedelta

REVIEW_FILE = "review.json"
USAGE_FILE = "usage.json"

def load_review():
    """โหลดข้อมูลรีวิวทั้งหมด (return dict)"""
    try:
        with open(REVIEW_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_review(data):
    """บันทึกข้อมูลรีวิวทั้งหมด (dict)"""
    try:
        with open(REVIEW_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[review_utils] Save error: {e}")

def set_review(user_id, rating):
    """
    เซ็ตคะแนนรีวิว (1-5) ให้ user_id ในวันที่วันนี้
    """
    user_id = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_review()
    data.setdefault(today, {})
    data[today][user_id] = int(rating)
    save_review(data)

def get_review(date, user_id):
    """
    ดึงรีวิว user_id ในวันที่กำหนด (คืน None ถ้าไม่มี)
    """
    user_id = str(user_id)
    data = load_review()
    return data.get(date, {}).get(user_id, None)

def has_reviewed_today(user_id):
    """
    เช็กว่า user_id ให้รีวิววันนี้แล้วหรือยัง (True/False)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    return get_review(today, user_id) is not None

def need_review_today(user_id):
    """
    เช็กว่าต้องให้ user_id รีวิววันนี้ไหม
    (หาก user ใช้บอทเมื่อวานและวันนี้ยังไม่รีวิว)
    """
    user_id = str(user_id)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            usage = json.load(f)
        # ถ้า user ใช้บอทเมื่อวาน แต่วันนี้ยังไม่ได้รีวิว
        if user_id in usage.get(yesterday, {}):
            return not has_reviewed_today(user_id)
    except Exception:
        pass
    return False
