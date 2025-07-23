# handlers/history.py
from utils.message_utils import send_message
from utils.history_utils import get_user_history  # เปลี่ยน path เป็น utils.history_utils

def handle_history(chat_id, user_text):
    """แสดงประวัติ 10 รายการล่าสุดของผู้ใช้"""
    user_id = str(chat_id)
    logs = get_user_history(user_id, limit=10)
    if not logs:
        send_message(chat_id, "🔍 คุณยังไม่มีประวัติการใช้งานเลยครับ")
        return

    text = "\n\n".join([
        f"🗓️ {item.get('date','')}\n❓{item.get('q','')}\n"
        f"{'💬 ' + item['a'] if item.get('a') else ''}"
        for item in logs
    ])
    send_message(chat_id, f"📜 ประวัติคำถามย้อนหลัง 10 รายการ:\n\n{text}")
