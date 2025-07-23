# utils/context_utils.py
import json
import os
from datetime import datetime

# ---- PATHS ----
CONTEXT_FILE   = os.getenv("CONTEXT_FILE",   "context_history.json")
LOCATION_FILE  = os.getenv("LOCATION_FILE",  "location_logs.json")

# ------------- Generic JSON helpers -------------
def _load_json(path: str) -> dict:
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[context_utils._load_json:{path}] {e}")
        return {}

def _save_json(data: dict, path: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils._save_json:{path}] {e}")

# ------------- Conversation context -------------
def get_context(user_id: str):
    return _load_json(CONTEXT_FILE).get(user_id, [])

def save_context(all_ctx: dict):
    _save_json(all_ctx, CONTEXT_FILE)

def update_context(user_id: str, text: str, keep_last: int = 6):
    all_ctx = _load_json(CONTEXT_FILE)
    all_ctx.setdefault(user_id, []).append(text)
    all_ctx[user_id] = all_ctx[user_id][-keep_last:]
    _save_json(all_ctx, CONTEXT_FILE)

def is_waiting_review(user_id: str) -> bool:
    ctx = get_context(user_id)
    return bool(ctx and ctx[-1] == "__wait_review__")

# ------------- Location helpers -------------
def get_user_location(user_id: str):
    return _load_json(LOCATION_FILE).get(user_id)

def update_location(user_id: str, lat: float, lon: float):
    data = _load_json(LOCATION_FILE)
    data[user_id] = {"lat": lat, "lon": lon, "ts": datetime.now().isoformat()}
    _save_json(data, LOCATION_FILE)

# ------------- Reset helper -------------
def reset_context(user_id: str):
    all_ctx = _load_json(CONTEXT_FILE)
    all_ctx[user_id] = []
    _save_json(all_ctx, CONTEXT_FILE)
