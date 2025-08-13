# handlers/favorite.py
# -*- coding: utf-8 -*-
"""
Handler for user favorites, now fully integrated with the persistent database.
This version combines all sub-commands (add, list, remove) into one handler.
"""
from __future__ import annotations
from typing import Dict, Any, List
import html

from utils.telegram_api import send_message
from utils.favorite_utils import add_new_favorite, get_user_favorites, remove_user_favorite

def _format_favorites_list(favs: List[Dict]) -> str:
    """Formats the list of favorites beautifully and safely."""
    if not favs:
        return "📭 คุณยังไม่มีรายการโปรดเลยครับ"
    
    lines = []
    for i, item in enumerate(favs, start=1):
        content = html.escape(item.get('content', ''))
        lines.append(f"{i}. <b>{content}</b>")
        
    return "⭐ <b>รายการโปรด 10 อันดับล่าสุดของคุณ:</b>\n" + "\n".join(lines)

def handle_favorite(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Handles all favorite sub-commands: /favorite_add, /favorite_list, /favorite_remove.
    """
    user_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    
    print(f"[handle_favorite] Request from user {user_name} (ID: {user_id})")

    try:
        command_part = user_text.strip().lower().split()[0]

        # --- Handles /favorite_add ---
        if command_part == "/favorite_add":
            content_to_add = user_text.replace(command_part, "", 1).strip()
            if not content_to_add:
                send_message(user_id, "วิธีใช้: /favorite_add <ข้อความที่ต้องการบันทึก>")
                return
            if add_new_favorite(user_id, content_to_add):
                send_message(user_id, f"✅ บันทึกรายการโปรดของคุณเรียบร้อยแล้วครับ, คุณ {user_name}")
            else:
                send_message(user_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการบันทึก")
            return

        # --- Handles /favorite_list ---
        if command_part == "/favorite_list":
            favorites_list = get_user_favorites(user_id, limit=10)
            formatted_message = _format_favorites_list(favorites_list)
            send_message(user_id, formatted_message, parse_mode="HTML")
            return

        # --- Handles /favorite_remove ---
        if command_part == "/favorite_remove":
            parts = user_text.split()
            if len(parts) < 2 or not parts[1].isdigit():
                send_message(user_id, "โปรดระบุลำดับ (ตัวเลข) ที่ต้องการลบ เช่น `/favorite_remove 2`")
                return
            index_to_remove = int(parts[1])
            if remove_user_favorite(user_id, index_to_remove):
                send_message(user_id, f"🗑️ ลบรายการที่ {index_to_remove} เรียบร้อยแล้วครับ")
            else:
                send_message(user_id, "❌ ไม่พบรายการตามลำดับที่ระบุ หรือเกิดข้อผิดพลาด")
            return
        
        # --- Fallback help message ---
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
