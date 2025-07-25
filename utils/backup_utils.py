# handlers/backup_status.py

from utils.backup_utils import get_backup_status
from utils.message_utils import send_message

def handle_backup_status(chat_id, user_text):
    """
    ตอบสถานะ backup ล่าสุดให้ผู้ใช้
    """
    status = get_backup_status()
    if not status:
        send_message(chat_id, "❌ ยังไม่พบข้อมูล backup ล่าสุดในระบบ หรือยังไม่เคยสำรองข้อมูลเลย")
        return

    last_backup = status['last_backup']
    files = ", ".join(status['files'])
    result = status['status']
    details = status.get('details', '')

    msg = (
        f"📦 <b>Backup ล่าสุด</b>\n"
        f"🕒 เวลา: <code>{last_backup}</code>\n"
        f"📄 ไฟล์: {files}\n"
        f"✅ สถานะ: <b>{result}</b>\n"
    )
    if details:
        msg += f"ℹ️ {details}\n"
    send_message(chat_id, msg, parse_mode="HTML")
