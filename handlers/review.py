# handlers/review.py

from review_utils import set_review, need_review_today
from utils.message_utils import send_message

def handle_review(chat_id, user_text):
    """
    ฟังก์ชันนี้จะถูกเรียกจาก main_handler เมื่อผู้ใช้ส่งข้อความ /review หรือเกี่ยวข้อง
    - ถ้ายังไม่ได้รีวิว จะขอให้กรอกคะแนน
    - ถ้ารับข้อความเป็น 1-5 จะบันทึกและขอบคุณ
    """
    user_id = str(chat_id)
    txt = user_text.strip()

    # ถ้าเป็นการขอรีวิว
    if need_review_today(user_id):
        if txt in ["1", "2", "3", "4", "5"]:
            set_review(user_id, int(txt))
            send_message(chat_id, "✅ ขอบคุณสำหรับรีวิวครับ!")
        else:
            send_message(chat_id, "❓ กรุณารีวิวความพึงพอใจการใช้บอทวันนี้ (1-5):")
    else:
        send_message(chat_id, "วันนี้ไม่จำเป็นต้องรีวิวครับ")
