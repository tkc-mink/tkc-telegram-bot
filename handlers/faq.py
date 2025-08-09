# handlers/faq.py
# -*- coding: utf-8 -*-

from utils.faq_utils import get_faq_list, add_faq
from utils.message_utils import send_message


def handle_faq(chat_id: int, user_text: str) -> None:
    """
    ใช้:
    - /faq                  -> แสดง FAQ ทั้งหมด
    - /add_faq <คำถาม>     -> เพิ่มคำถามเข้ารายการ FAQ
    """
    try:
        text = (user_text or "").strip()

        if text.startswith("/add_faq"):
            q = text.replace("/add_faq", "", 1).strip()
            if not q:
                send_message(chat_id, "โปรดพิมพ์คำถามต่อท้ายคำสั่ง เช่น /add_faq วิธีเช็คสภาพอากาศ")
                return

            add_faq(q)
            send_message(chat_id, f"✅ เพิ่มคำถามใน FAQ: {q}")
            return

        # แสดงรายการ FAQ ทั้งหมด
        faq = get_faq_list()
        if faq:
            msg = "📚 <b>FAQ (คำถามที่พบบ่อย)</b>:\n" + "\n".join(f"• {q}" for q in faq)
        else:
            msg = "ยังไม่มีรายการ FAQ ครับ"
        send_message(chat_id, msg, parse_mode="HTML")

    except Exception as e:
        send_message(chat_id, f"❌ จัดการ FAQ ไม่สำเร็จ: {e}")
