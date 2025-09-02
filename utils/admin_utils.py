# utils/admin_utils.py
# -*- coding: utf-8 -*-
"""
Contains the business logic for all admin commands, ensuring separation
of concerns from the handlers.
"""
from __future__ import annotations
from typing import Dict, Any
import os

# --- ✅ ส่วนที่เราแก้ไข: import เครื่องมือที่จำเป็นจาก memory_store และ telegram_api ---
from utils.memory_store import get_all_users, update_user_status, get_user_by_id
from utils.telegram_api import send_message

# --- ✅ ดึง ID ของ Super Admin มาจาก Environment Variable ---
# **สำคัญ:** คุณต้องไปตั้งค่า SUPER_ADMIN_ID ใน Environment Variables บน Render ด้วยนะครับ
# โดยใส่ค่าเป็น Telegram User ID ของคุณชลิต
try:
    SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
except (ValueError, TypeError):
    print("[Admin] ERROR: SUPER_ADMIN_ID is not a valid integer. Admin features will be disabled.")
    SUPER_ADMIN_ID = 0

def is_super_admin(user_id: int) -> bool:
    """
    ตรวจสอบว่า user_id ที่ระบุเป็น Super Admin หรือไม่
    """
    if not SUPER_ADMIN_ID:
        return False # ถ้าไม่ได้ตั้งค่า ID ไว้ ก็ไม่มีใครเป็นแอดมินได้
    return user_id == SUPER_ADMIN_ID

def notify_super_admin_for_approval(new_user_data: Dict[str, Any]):
    """
    ส่งข้อความแจ้งเตือน Super Admin เมื่อมีผู้ใช้ใหม่รอการอนุมัติ
    """
    if not SUPER_ADMIN_ID:
        print("[Admin] SUPER_ADMIN_ID is not set. Cannot send new user notification.")
        return
        
    user_id = new_user_data.get('id')
    first_name = new_user_data.get('first_name', '')
    username = new_user_data.get('username', 'N/A')
    
    # จัดรูปแบบข้อความให้สวยงามและใช้งานง่าย
    message = (
        f"🔔 **มีผู้ใช้ใหม่รอการอนุมัติครับ** 🔔\n\n"
        f"**ชื่อ:** {first_name}\n"
        f"**Username:** @{username}\n"
        f"**User ID:** `{user_id}`\n\n"
        f"ใช้คำสั่ง `/admin_approve {user_id}` เพื่ออนุมัติ หรือ `/admin_remove {user_id}` เพื่อปฏิเสธครับ"
    )
    send_message(SUPER_ADMIN_ID, message, parse_mode="Markdown")

def approve_user(target_user_id: int) -> str:
    """
    ตรรกะสำหรับการอนุมัติผู้ใช้:
    1. อัปเดตสถานะในฐานข้อมูลเป็น 'approved'
    2. ส่งข้อความยืนยันกลับไปยัง Super Admin
    3. ส่งข้อความต้อนรับไปยังผู้ใช้ที่เพิ่งได้รับการอนุมัติ
    """
    if update_user_status(target_user_id, "approved"):
        target_user = get_user_by_id(target_user_id)
        if target_user:
            # แจ้งกลับไปยังผู้ใช้ที่เพิ่งได้รับการอนุมัติ
            welcome_message = (
                "🎉 ยินดีด้วยครับ! บัญชีของคุณได้รับการอนุมัติให้เข้าใช้งาน 'TKC Assistant' เรียบร้อยแล้ว\n\n"
                "พิมพ์ /help เพื่อดูรายการคำสั่งทั้งหมดที่ใช้ได้ หรือเริ่มพูดคุยกับผมได้เลยครับ!"
            )
            send_message(target_user_id, welcome_message)
        return f"✅ อนุมัติผู้ใช้ ID: {target_user_id} ({target_user.get('first_name', '')}) เรียบร้อยแล้วครับ"
    else:
        return f"❓ ไม่พบผู้ใช้ ID: {target_user_id} ในระบบ หรือเกิดข้อผิดพลาดในการอัปเดตสถานะครับ"

def list_all_users() -> str:
    """
    สร้างข้อความสรุปรายชื่อผู้ใช้ทั้งหมดในระบบ พร้อมสถานะและบทบาท
    """
    users = get_all_users()
    if not users:
        return "ยังไม่มีผู้ใช้ในระบบเลยครับ"
    
    lines = ["**รายชื่อผู้ใช้ทั้งหมดในระบบ:**"]
    for user in users:
        status_icon = "✅" if user['status'] == 'approved' else ("⏳" if user['status'] == 'pending' else "❌")
        lines.append(f"{status_icon} `{user['user_id']}` - {user['first_name']} (@{user['username']}) [{user['role']}]")
    
    return "\n".join(lines)
