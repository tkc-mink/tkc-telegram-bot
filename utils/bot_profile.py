# utils/bot_profile.py
# -*- coding: utf-8 -*-
"""
Manages the bot's personality, including its name, gender, and tone.
"""
import json
import os
import re

PROFILE_FILE = "data/bot_profile.json"

# ✅ ตั้งค่าโปรไฟล์ "ชิบะน้อย" เป็นค่าเริ่มต้น
DEFAULT_PROFILE = {
    "gender": "male",
    "nickname": "ชิบะน้อย",
    "self_pronoun": "ชิบะน้อย", # เปลี่ยนจาก "ผม" เป็น "ชิบะน้อย" เพื่อความน่ารัก
    "default_user_pronoun": "คุณ"
}

def get_bot_profile():
    """Loads the bot's profile from a JSON file, or creates it if it doesn't exist."""
    try:
        if not os.path.exists(PROFILE_FILE):
            set_bot_profile(**DEFAULT_PROFILE)
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROFILE

def set_bot_profile(**kwargs):
    """Updates and saves the bot's profile."""
    profile = get_bot_profile()
    profile.update(kwargs)
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

def bot_intro():
    """Generates the bot's standard introduction message."""
    # ✅ ปรับปรุงคำแนะนำตัวให้น่ารักขึ้น
    profile = get_bot_profile()
    return (
        f"โฮ่ง! {profile['nickname']}มารายงานตัวแล้วครับ! "
        f"มีอะไรให้{profile['nickname']}รับใช้ บอกได้เลยนะครับ 🐾"
    )

def adjust_bot_tone(text: str) -> str:
    """
    Adjusts the bot's tone to be consistently male and polite ("ชิบะน้อย").
    Ensures text ends with "ครับ" and uses the correct pronouns.
    """
    if not text:
        return ""
    
    # ✅ ปรับปรุงการแทนตัวเองให้เป็น "ชิบะน้อย" และลงท้ายให้สุภาพ
    # แทนที่คำว่า "ฉัน", "ดิฉัน", "หนู", "เรา", "ผม" ด้วย "ชิบะน้อย"
    pronoun_pattern = r'\b(ฉัน|ดิฉัน|หนู|เรา|ผม)\b'
    text = re.sub(pronoun_pattern, 'ชิบะน้อย', text)

    # แทนที่คำลงท้าย นะคะ/คะ/ค่ะ เป็น ครับ
    text = text.replace("ค่ะ", "ครับ").replace("คะ", "ครับ").replace("นะคะ", "นะครับ")
    
    # ตรวจสอบว่าลงท้ายด้วย "ครับ" หรือยัง
    if not text.endswith(("ครับ", "คร้าบ", "ค้าบ")):
        # ลบเครื่องหมายลงท้ายอื่นๆ ที่อาจมี
        text = text.rstrip('.!?')
        text += " ครับ"
        
    return text
