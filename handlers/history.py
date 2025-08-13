# handlers/history.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from utils.memory_store import get_user_chat_history
from utils.telegram_api import send_message
import datetime

def handle_history(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id, user_id = user_info['profile']['user_id'], user_info['profile']['user_id']
    history = get_user_chat_history(user_id)
    if not history:
        send_message(chat_id, "ยังไม่มีประวัติการสนทนาครับ")
        return
    
    message = "**ประวัติการสนทนา 10 รายการล่าสุด:**\n\n"
    for item in reversed(history):
        ts = datetime.datetime.fromisoformat(item['timestamp']).strftime('%H:%M') if 'timestamp' in item else ''
        role = "คุณ" if item['role'] == 'user' else "ผม"
        content = item['content']
        if len(content) > 100: content = content[:100] + "..."
        message += f"`{ts}` **{role}:** {content}\n"
        
    send_message(chat_id, message, parse_mode="Markdown")
