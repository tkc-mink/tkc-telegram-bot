# handlers/faq.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from utils.memory_store import add_or_update_faq, get_faq_answer, get_all_faqs
from utils.telegram_api import send_message

def handle_faq(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id, user_id = user_info['profile']['user_id'], user_info['profile']['user_id']
    parts = user_text.split(maxsplit=2)
    command = parts[0].lower()

    # /add_faq <keyword> <answer>
    if command == "/add_faq":
        if len(parts) < 3:
            send_message(chat_id, "วิธีใช้: /add_faq <คำถาม> <คำตอบ>")
            return
        keyword, answer = parts[1], parts[2]
        if add_or_update_faq(keyword, answer, user_id):
            send_message(chat_id, f"✅ บันทึก FAQ สำหรับคำว่า '{keyword}' เรียบร้อยแล้วครับ")
        else:
            send_message(chat_id, "❌ เกิดข้อผิดพลาดในการบันทึก FAQ")
        return

    # /faq <keyword>
    if len(parts) > 1:
        keyword = parts[1]
        answer = get_faq_answer(keyword)
        if answer:
            send_message(chat_id, f"💡 **คำตอบสำหรับ '{keyword}':**\n\n{answer}")
        else:
            send_message(chat_id, f"❓ ไม่พบคำตอบสำหรับ '{keyword}' ครับ")
    # /faq (list all)
    else:
        faqs = get_all_faqs()
        if not faqs:
            send_message(chat_id, "ยังไม่มี FAQ ในระบบครับ ใช้ /add_faq เพื่อเพิ่มได้เลย")
            return
        message = "**รายการ FAQ ทั้งหมด:**\n" + "\n".join(f"- `{item['keyword']}`" for item in faqs)
        send_message(chat_id, message, parse_mode="Markdown")
