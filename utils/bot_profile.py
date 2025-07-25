import json

PROFILE_FILE = "data/bot_profile.json"

def get_bot_profile():
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Default (fallback)
        return {
            "gender": "male",
            "nickname": "ชิบะน้อย",
            "self_pronoun": "ผม",
            "default_user_pronoun": "คุณ"
        }

def set_bot_profile(**kwargs):
    prof = get_bot_profile()
    prof.update(kwargs)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=2)
