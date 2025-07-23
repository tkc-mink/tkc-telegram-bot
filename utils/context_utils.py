# context_utils.py

import json
import os

CONTEXT_FILE = "context_logs.json"

def load_context(user_id):
    """โหลด context ทั้งหมดของ user (list of message-dict)"""
    try:
        if not os.path.exists(CONTEXT_FILE):
            return []
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(user_id, [])
    except Exception as e:
        print(f"[context_utils.load_context] {e}")
        return []

def save_context(user_id, context):
    """เซฟ context (list of message-dict) ของ user"""
    try:
        data = {}
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        data[user_id] = context
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils.save_context] {e}")

def add_user_message(user_id, text):
    """เพิ่ม message จาก user"""
    context = load_context(user_id)
    context.append({"role": "user", "content": text})
    save_context(user_id, context)

def add_assistant_message(user_id, text):
    """เพิ่ม message จาก assistant"""
    context = load_context(user_id)
    context.append({"role": "assistant", "content": text})
    save_context(user_id, context)

def get_last_messages(user_id, n=6):
    """
    ดึง message ล่าสุด n รายการของ user (ทั้ง user และ assistant)
    Format สำหรับ OpenAI API: [{"role":"user","content":"..."}, ...]
    """
    context = load_context(user_id)
    return context[-n:] if context else []

def clear_context(user_id):
    """ลบ context ทั้งหมดของ user"""
    try:
        data = {}
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        if user_id in data:
            del data[user_id]
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils.clear_context] {e}")

def clear_all_context():
    """ลบ context ของทุก user (admin use)"""
    try:
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[context_utils.clear_all_context] {e}")

def list_all_users():
    """คืนรายชื่อ user_id ที่มี context เก็บอยู่ (for admin/debug)"""
    try:
        if not os.path.exists(CONTEXT_FILE):
            return []
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data.keys())
    except Exception as e:
        print(f"[context_utils.list_all_users] {e}")
        return []
