import os
import json
from datetime import datetime

HISTORY_FILE = os.getenv("HISTORY_FILE", "history.json")

def load_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return {}
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[history_utils.load_history] {e}")
        return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[history_utils.save_history] {e}")

def log_message(user_id, question, answer):
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = load_history()
    data.setdefault(user_id, [])
    data[user_id].append({
        "date": today,
        "q": question,
        "a": answer
    })
    # เก็บแค่ 100 ข้อความล่าสุด/คน
    data[user_id] = data[user_id][-100:]
    save_history(data)

def get_user_history(user_id, limit=10):
    data = load_history()
    history = data.get(user_id, [])
    # เอาแค่ล่าสุด (limit)
    return history[-limit:]
