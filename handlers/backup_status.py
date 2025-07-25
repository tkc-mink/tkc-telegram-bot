# handlers/backup_status.py
from utils.message_utils import send_message
from utils.backup_utils import get_backup_status  # ต้องมีฟังก์ชันนี้

def handle_backup_status(chat_id, user_text):
    status = get_backup_status()   # เช่น {'last_backup': '2025-07-25 17:30', 'files': 4, ...}
    if not status:
        send_message(chat_id, "ยังไม่มีข้อมูลการสำรองล่าสุดในระบบ")
        return
    msg = (
        f"📦 Backup ล่าสุด: {status['last_backup']}\n"
        f"จำนวนไฟล์: {status['files']}\n"
        f"สถานะ: {status['result']}\n"
    )
    send_message(chat_id, msg)
