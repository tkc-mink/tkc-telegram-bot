# handlers/favorite.py
# -*- coding: utf-8 -*-
"""
Handler for user favorites, now fully integrated with the persistent database.
"""
from __future__ import annotations
from typing import Dict, Any

from utils.telegram_api import send_message
from utils.favorite_utils import add_new_favorite, get_user_favorites, remove_user_favorite

def handle_favorite(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Handles favorite commands: /favorite_add, /favorite_list, /favorite_remove.
    """
    user_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    
    print(f"[handle_favorite] Request from user {user_name} (ID: {user_id})")

    try:
        text = user_text.strip().lower()

        # /favorite_add <ข้อความ>
        if text.startswith("/favorite_add"):
            content = user_text.replace("/favorite_add", "", 1).strip()
            if not content:
                send_message(user_id, "วิธีใช้: /favorite_add <ข้อความที่ต้องการบันทึก>")
                return
            if add_new_favorite(user_id, content):
                send_message(user_id, f"✅ บันทึกรายการโปรดของคุณเรียบร้อยแล้วครับ, คุณ {user_name}")
            else:
                send_message(user_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการบันทึก")
            return

        # /favorite_list
        if text.startswith("/favorite_list"):
            favs = get_user_favorites(user_id, limit=10)
            if not favs:
                send_message(user_id, "🤔 คุณยังไม่มีรายการโปรดเลยครับ ใช้ /favorite_add เพื่อเริ่มบันทึกได้เลย")
                return
            lines = [f"{i}. {item['content']}" for i, item in enumerate(favs, start=1)]
            msg = "⭐ **รายการโปรด 10 อันดับล่าสุดของคุณ:**\n" + "\n".join(lines)
            send_message(user_id, msg, parse_mode="Markdown")
            return

        # /favorite_remove <ลำดับ>
        if text.startswith("/favorite_remove"):
            parts = user_text.split()
            if len(parts) < 2 or not parts[1].isdigit():
                send_message(user_id, "โปรดระบุลำดับ (ตัวเลข) ที่ต้องการลบ เช่น `/favorite_remove 2`")
                return
            idx = int(parts[1])
            if remove_user_favorite(user_id, idx):
                send_message(user_id, f"🗑️ ลบรายการที่ {idx} เรียบร้อยแล้วครับ")
            else:
                send_message(user_id, "❌ ไม่พบรายการตามลำดับที่ระบุ หรือเกิดข้อผิดพลาด")
            return
        
        # ถ้าไม่ตรงกับคำสั่งไหนเลย
        help_text = (
            "**คำสั่งสำหรับจัดการรายการโปรด:**\n"
            "• `/favorite_add <ข้อความ>`\n"
            "• `/favorite_list`\n"
            "• `/favorite_remove <ลำดับ>`"
        )
        send_message(user_id, help_text, parse_mode="Markdown")

    except Exception as e:
        print(f"[handle_favorite] An unhandled error occurred: {e}")
        send_message(user_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดในระบบจัดการรายการโปรดครับ")
