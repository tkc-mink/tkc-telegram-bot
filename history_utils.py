# history_utils.py

import json
from datetime import datetime

HISTORY_FILE = "history.json"

def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

def log_message(user_id, question, answer):
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_history()
    data.setdefault(user_id, [])
    data[user_id].append({
        "date": today,
        "q": question,
        "a": answer
    })
    # เก็บแค่ 100 ข้อความล่าสุด/คน (หรือจะเก็บมากกว่านี้ก็ได้)
    data[user_id] = data[user_id][-100:]
    save_history(data)

def get_user_history(user_id, limit=10):
    data = load_history()
    history = data.get(user_id, [])
    # เอาแค่ล่าสุด (limit)
    return history[-limit:]
