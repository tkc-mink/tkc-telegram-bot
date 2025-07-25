from utils.backup_utils import get_backup_status

def handle_backup_status(chat_id, user_text):
    info = get_backup_status()   # อ่านข้อมูล backup ล่าสุด (อ่านจาก log หรือไฟล์ JSON)
    # ส่งข้อความสรุปให้ user
    if info:
        message = (
            f"🟢 Backup ล่าสุด\n"
            f"- วันที่: {info['date']}\n"
            f"- ไฟล์: {info['filename']}\n"
            f"- ขนาด: {info['size']} bytes\n"
            f"- สถานะ: {'สำเร็จ' if info['success'] else 'ผิดพลาด'}"
        )
    else:
        message = "ยังไม่พบข้อมูล backup ล่าสุด"
    from utils.message_utils import send_message   # local import ป้องกัน import วน
    send_message(chat_id, message)
