# utils/context_utils.py
import json
import os
from datetime import datetime

# ------- Files -------
CONTEXT_FILE   = os.getenv("CONTEXT_FILE",   "context_history.json")
LOCATION_FILE  = os.getenv("LOCATION_FILE",  "location_logs.json")

# ------- JSON helpers -------
def _load_json(path):
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(data, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils] save {path} error: {e}")

# ------- Conversation context -------
def get_context(user_id):
    data = _load_json(CONTEXT_FILE)
    return data.get(user_id, [])

def update_context(user_id, text, max_keep=6):
    data = _load_json(CONTEXT_FILE)
    data.setdefault(user_id, []).append(text)
    data[user_id] = data[user_id][-max_keep:]
    _save_json(data, CONTEXT_FILE)

def is_waiting_review(user_id):
    ctx = get_context(user_id)
    return bool(ctx and ctx[-1] == "__wait_review__")

# ------- Location -------
def get_user_location(user_id):
    loc = _load_json(LOCATION_FILE)
    return loc.get(user_id)

def update_location(user_id, lat, lon):
    loc = _load_json(LOCATION_FILE)
    loc[user_id] = {
        "lat": lat,
        "lon": lon,
        "ts": datetime.now().isoformat()
    }
    _save_json(loc, LOCATION_FILE)
