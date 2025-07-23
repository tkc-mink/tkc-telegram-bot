# handlers/history.py

from utils.history_utils import get_user_history
from utils.message_utils import send_message

def handle_history(chat_id, user_text):
    """
    Handler สำหรับแสดงประวัติการใช้งานย้อนหลัง 10 รายการล่าสุด
    :param chat_id: ไอดีแชทของผู้ใช้
    :param user_text: ข้อความที่ผู้ใช้ส่งมา (ไม่ได้ใช้ในฟังก์ชันนี้โดยตรง)
    """
    user_id = str(chat_id)
    logs = get_user_history(user_id, limit=10)
    if not logs or len(logs) == 0:
        send_message(chat_id, "🔍 คุณยังไม่มีประวัติการใช้งานเลยครับ")
        return

    lines = []
    for l in logs:
        date = l.get('date', '')
        q    = l.get('q', '')
        a    = l.get('a', '')
        answer_line = f"💬 {a}" if a else ""
        lines.append(f"🗓️ {date}\n❓{q}\n{answer_line}")

    text = "\n\n".join(lines)
    send_message(chat_id, f"📜 ประวัติคำถามย้อนหลัง 10 รายการ:\n\n{text}")
