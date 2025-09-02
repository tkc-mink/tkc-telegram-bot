# utils/admin_utils.py
# -*- coding: utf-8 -*-
"""
Contains the business logic for all admin commands, ensuring separation
of concerns from the handlers. This is the final, correct version.
"""
from __future__ import annotations
from typing import Dict, Any
import os

# --- ✅ ส่วนที่แก้ไข: import เครื่องมือที่ถูกต้องจาก memory_store ---
from utils.memory_store import (
    get_all_users,      # ใช้สำหรับดึงรายชื่อผู้ใช้ทั้งหมด
    update_user_status, # ใช้สำหรับเปลี่ยนสถานะ (อนุมัติ/ลบ)
    get_user_by_id      # ใช้สำหรับดึงข้อมูลผู้ใช้รายคน
)
from utils.telegram_api import send_message

# --- ดึง ID ของ Super Admin มาจาก Environment Variable ---
# **สำคัญ:** คุณต้องไปตั้งค่า SUPER_ADMIN_ID ใน Environment Variables บน Render
# โดยใส่ค่าเป็น Telegram User ID ของคุณ
try:
    SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
except (ValueError, TypeError):
    print("[Admin] ERROR: SUPER_ADMIN_ID is not a valid integer. Admin features will be disabled.")
    SUPER_ADMIN_ID = 0

def is_super_admin(user_id: int) -> bool:
    """ตรวจสอบว่า user ID นี้เป็น Super Admin หรือไม่"""
    if not SUPER_ADMIN_ID:
        return False
    return user_id == SUPER_ADMIN_ID

def notify_super_admin_for_approval(new_user_data: Dict[str, Any]):
    """ส่งข้อความแจ้งเตือน Super Admin เมื่อมีผู้ใช้ใหม่รออนุมัติ"""
    if not SUPER_ADMIN_ID:
        print("[Admin] SUPER_ADMIN_ID is not set. Cannot send new user notification.")
        return
        
    user_id = new_user_data.get('id')
    first_name = new_user_data.get('first_name', '')
    username = new_user_data.get('username', 'N/A')
    
    message = (
        f"🔔 **มีผู้ใช้ใหม่รอการอนุมัติครับ** 🔔\n\n"
        f"**ชื่อ:** {first_name}\n"
        f"**Username:** @{username}\n"
        f"**User ID:** `{user_id}`\n\n"
        f"ใช้คำสั่ง `/admin_approve {user_id}` เพื่ออนุมัติ หรือ `/admin_remove {user_id}` เพื่อปฏิเสธครับ"
    )
    send_message(SUPER_ADMIN_ID, message, parse_mode="Markdown")

def approve_user(target_user_id: int) -> str:
    """ตรรกะสำหรับการอนุมัติผู้ใช้"""
    if update_user_status(target_user_id, "approved"):
        target_user = get_user_by_id(target_user_id)
        if target_user:
            send_message(target_user_id, "🎉 ยินดีด้วยครับ! บัญชีของคุณได้รับการอนุมัติให้เข้าใช้งาน 'ชิบะน้อย' เรียบร้อยแล้ว\n\nพิมพ์ /help เพื่อดูคำสั่งทั้งหมดได้เลยครับ")
        return f"✅ อนุมัติผู้ใช้ ID: {target_user_id} เรียบร้อยแล้วครับ"
    else:
        return f"❓ ไม่พบผู้ใช้ ID: {target_user_id} หรือเกิดข้อผิดพลาดในการอัปเดตสถานะครับ"

def remove_user(target_user_id: int) -> str:
    """ตรรกะสำหรับการลบ/ระงับผู้ใช้"""
    if update_user_status(target_user_id, "removed"):
        target_user = get_user_by_id(target_user_id)
        name = target_user.get('first_name', '') if target_user else ''
        send_message(target_user_id, "บัญชีของคุณถูกระงับการใช้งานแล้วครับ")
        return f"🚫 ระงับการใช้งานผู้ใช้ ID: {target_user_id} ({name}) เรียบร้อยแล้วครับ"
    else:
        return f"❓ ไม่พบผู้ใช้ ID: {target_user_id} หรือเกิดข้อผิดพลาดครับ"

def list_all_users() -> str:
    """สร้างข้อความสรุปรายชื่อผู้ใช้ทั้งหมดในระบบ"""
    users = get_all_users()
    if not users:
        return "ยังไม่มีผู้ใช้ในระบบเลยครับ"
    
    lines = ["**รายชื่อผู้ใช้ทั้งหมดในระบบ:**"]
    for user in users:
        status_icon = {"approved": "✅", "pending": "⏳", "removed": "❌"}.get(user['status'], "❓")
        lines.append(f"{status_icon} `{user['user_id']}` - {user['first_name']} (@{user['username']}) [{user['role']}]")
    
    return "\n".join(lines)
