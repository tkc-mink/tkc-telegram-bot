# handlers/faq.py
from utils.faq_utils import get_faq_list, add_faq
from utils.message_utils import send_message

def handle_faq(chat_id, user_text):
    """/faq = ดู FAQ, /add_faq ... = เพิ่ม FAQ"""
    text = user_text.strip()
    if text.startswith("/add_faq"):
        q = text.replace("/add_faq", "", 1).strip()
        if not q:
            send_message(chat_id, "❗️ ส่ง /add_faq <คำถามที่พบบ่อย>")
            return
        add_faq(q)
        send_message(chat_id, f"⭐️ เพิ่มคำถาม FAQ: {q}")
    else:
        faq = get_faq_list()
        if faq:
            msg = "⭐️ <b>FAQ (คำถามที่พบบ่อย):</b>\n" + "\n".join(f"• {q}" for q in faq)
        else:
            msg = "ยังไม่มี FAQ ที่บันทึก"
        send_message(chat_id, msg, parse_mode="HTML")
