# utils/admin_utils.py
# -*- coding: utf-8 -*-
"""
Admin utilities for managing user access and bot functions.
This module now uses the updated memory_store functions.
"""
import os
from typing import Dict, Any, Optional

# --- ✅ **ส่วนที่แก้ไข:** เปลี่ยนชื่อฟังก์ชันที่ Import ให้ถูกต้อง ---
from utils.memory_store import (
    load_all_user_profiles, # ✅ เปลี่ยนจาก get_all_users
    update_user_profile,    # ✅ เปลี่ยนจาก update_user_status
    get_user_by_id
)
from utils.telegram_api import send_message, reply_keyboard

SUPER_ADMIN_ID = os.getenv("SUPER_ADMIN_ID")

def is_super_admin(user_id: int) -> bool:
    """Checks if the given user ID is the SUPER_ADMIN_ID."""
    return str(user_id) == str(SUPER_ADMIN_ID)

def approve_user(admin_chat_id: int, target_user_id: int) -> str:
    """Approves a user to use the bot."""
    user_profile = get_user_by_id(target_user_id)
    if not user_profile:
        return f"ชิบะน้อยหาผู้ใช้ ID {target_user_id} ไม่เจอครับ"
    
    if user_profile.get("is_approved", False):
        return f"ผู้ใช้ {user_profile.get('first_name', '')} (ID: {target_user_id}) ได้รับอนุมัติอยู่แล้วครับ"

    user_profile['is_approved'] = True
    # ✅ ใช้ update_user_profile เพื่ออัปเดตข้อมูลผู้ใช้
    update_user_profile(user_profile)
    
    send_message(target_user_id, "🎉 เย้! คุณได้รับอนุญาตให้ใช้บอทของชิบะน้อยแล้วครับ")
    return f"✅ อนุมัติผู้ใช้ {user_profile.get('first_name', '')} (ID: {target_user_id}) เรียบร้อยครับ"

def list_all_users() -> str:
    """Lists all registered users with their status."""
    # ✅ ใช้ load_all_user_profiles เพื่อดึงข้อมูลผู้ใช้ทั้งหมด
    all_users = load_all_user_profiles()
    if not all_users:
        return "ตอนนี้ยังไม่มีใครคุยกับชิบะน้อยเลยครับ"

    messages = ["👤 รายชื่อผู้ใช้ทั้งหมด:"]
    for user_id_str, profile in all_users.items():
        user_id = int(user_id_str)
        status = "✅ อนุมัติแล้ว" if profile.get("is_approved") else "⏳ รออนุมัติ"
        name = profile.get("first_name", f"ไม่ระบุ ({user_id})")
        messages.append(f"- {name} (ID: {user_id}) : {status}")
    return "\n".join(messages)

def remove_user(admin_chat_id: int, target_user_id: int) -> str:
    """Removes a user's approval to use the bot."""
    user_profile = get_user_by_id(target_user_id)
    if not user_profile:
        return f"ชิบะน้อยหาผู้ใช้ ID {target_user_id} ไม่เจอครับ"
    
    if not user_profile.get("is_approved", False):
        return f"ผู้ใช้ {user_profile.get('first_name', '')} (ID: {target_user_id}) ไม่ได้รับอนุมัติอยู่แล้วครับ"

    user_profile['is_approved'] = False
    # ✅ ใช้ update_user_profile เพื่ออัปเดตข้อมูลผู้ใช้
    update_user_profile(user_profile)

    send_message(target_user_id, "😢 คุณไม่ได้รับอนุญาตให้ใช้บอทของชิบะน้อยแล้วครับ")
    return f"🚫 ถอนการอนุมัติผู้ใช้ {user_profile.get('first_name', '')} (ID: {target_user_id}) เรียบร้อยครับ"

def get_admin_commands_keyboard():
    """Returns an inline keyboard for admin commands."""
    return reply_keyboard([
        ["อนุมัติผู้ใช้"],
        ["ลบผู้ใช้"],
        ["ดูผู้ใช้ทั้งหมด"]
    ], one_time=False, resize=True)
