# utils/bot_profile.py

import json
import os

PROFILE_FILE = "data/bot_profile.json"
DEFAULT_PROFILE = {
    "gender": "male",
    "nickname": "ชิบะน้อย",
    "self_pronoun": "ผม",
    "default_user_pronoun": "คุณ"
}

def get_bot_profile():
    try:
        if not os.path.exists(PROFILE_FILE):
            set_bot_profile(**DEFAULT_PROFILE)
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROFILE

def set_bot_profile(**kwargs):
    profile = get_bot_profile()
    profile.update(kwargs)
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

def bot_intro():
    profile = get_bot_profile()
    return f"ผมชื่อ{profile['nickname']}นะครับ ยินดีให้คำปรึกษาครับ"

def adjust_bot_tone(text):
    # ปรับคำแทนตัวเองอัตโนมัติให้ดูสุภาพและเหมาะกับบอทผู้ชาย
    rep = text.replace("ฉัน", "ผม").replace("ดิฉัน", "ผม") \
              .replace("ค่ะ", "ครับ").replace("คะ", "ครับ") \
              .replace("หนู", "ผม").replace("เรา", "ผม")
    return rep
