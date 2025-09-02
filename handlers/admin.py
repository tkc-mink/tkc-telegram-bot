# handlers/admin.py
# -*- coding: utf-8 -*-
"""
Handler for all Super Admin commands.
This file acts as the entry point, validates permissions, and routes
commands to the appropriate logic in admin_utils.
"""
from __future__ import annotations
from typing import Dict, Any

# --- ✅ ส่วนที่เราแก้ไข: import เครื่องมือที่จำเป็น ---
from utils.telegram_api import send_message
from utils.admin_utils import is_super_admin, approve_user, list_all_users, remove_user # เพิ่ม remove_user

def handle_admin_command(user_info: Dict[str, Any], user_text: str) -> None:
    """
    The main entry point for all admin commands.
    It first checks for Super Admin privileges before dispatching the command.
    """
    user_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    
    # --- 1. Security Check: ตรวจสอบว่าเป็น Super Admin หรือไม่ ---
    if not is_super_admin(user_id):
        print(f"[Admin] Unauthorized access attempt by user {user_name} (ID: {user_id})")
        send_message(user_id, "⛔️ ขออภัยครับ คุณไม่มีสิทธิ์ใช้คำสั่งสำหรับผู้ดูแลระบบครับ")
        return
        
    parts = user_text.strip().split()
    command = parts[0].lower()
    
    print(f"[Admin] Received command '{command}' from Super Admin {user_name}")

    # --- 2. Command Router: แยกการทำงานตามคำสั่ง ---
    try:
        if command == "/admin_approve":
            if len(parts) < 2 or not parts[1].isdigit():
                send_message(user_id, "วิธีใช้ที่ถูกต้อง: `/admin_approve <user_id>`")
                return
            target_user_id = int(parts[1])
            reply = approve_user(target_user_id)
            send_message(user_id, reply, parse_mode="Markdown")
            
        elif command == "/admin_users":
            reply = list_all_users()
            send_message(user_id, reply, parse_mode="Markdown")
            
        elif command == "/admin_remove":
            if len(parts) < 2 or not parts[1].isdigit():
                send_message(user_id, "วิธีใช้ที่ถูกต้อง: `/admin_remove <user_id>`")
                return
            target_user_id = int(parts[1])
            reply = remove_user(target_user_id)
            send_message(user_id, reply, parse_mode="Markdown")

        # เพิ่มคำสั่งอื่นๆ ที่นี่ในอนาคต เช่น /admin_role
        else:
            send_message(user_id, f"ผมไม่รู้จักคำสั่งผู้ดูแลระบบ '{command}' ครับ ลองใช้ /help ดูนะครับ")
            
    except Exception as e:
        print(f"[handle_admin_command] An unhandled error occurred: {e}")
        send_message(user_id, f"❌ ขออภัยครับ เกิดข้อผิดพลาดในการทำงานของคำสั่งแอดมิน: {e}")
