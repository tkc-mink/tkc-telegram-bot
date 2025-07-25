import json
import os

PROFILE_FILE = "data/bot_profile.json"

_DEFAULT = {
    "gender": "male",
    "nickname": "ชิบะน้อย",
    "self_pronoun": "ผม",
    "default_user_pronoun": "คุณ"
}

def get_bot_profile():
    if not os.path.exists(PROFILE_FILE):
        set_bot_profile(**_DEFAULT)
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _DEFAULT

def set_bot_profile(**kwargs):
    prof = get_bot_profile()
    prof.update(kwargs)
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=2)
