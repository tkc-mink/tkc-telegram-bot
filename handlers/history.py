# handlers/history.py

from history_utils import get_user_history
from utils.message_utils import send_message

def handle_history(chat_id, user_text):
    """
    Handler สำหรับแสดงประวัติการใช้งานย้อนหลัง 10 รายการล่าสุด
    :param chat_id: ไอดีแชทของผู้ใช้
    :param user_text: ข้อความที่ผู้ใช้ส่งมา (ไม่ได้ใช้ในฟังก์ชันนี้โดยตรง)
    """
    user_id = str(chat_id)  # สำหรับระบบเดิม user_id == chat_id
    logs = get_user_history(user_id, limit=10)
    if not logs:
        send_message(chat_id, "🔍 คุณยังไม่มีประวัติการใช้งานเลยครับ")
        return
    text = "\n\n".join([
        f"🗓️ {l['date']}\n❓{l['q']}\n{'💬 '+l['a'] if 'a' in l else ''}"
        for l in logs
    ])
    send_message(chat_id, f"📜 ประวัติคำถามย้อนหลัง 10 รายการ:\n\n{text}")
