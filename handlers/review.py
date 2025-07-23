# handlers/review.py
from utils.message_utils import send_message
from utils.context_utils import update_context, is_waiting_review
from utils.review_utils import set_review, need_review_today

def handle_review(chat_id: int, user_text: str):
    user_id = str(chat_id)
    # ถ้าระบบคุณใช้ context เพื่อตรวจว่า "กำลังรอรีวิว" หรือไม่
    if need_review_today(user_id) and not is_waiting_review(user_id):
        send_message(chat_id, "❓ กรุณารีวิววันนี้ (1-5):")
        update_context(user_id, "__wait_review__")
        return

    # ถ้าอยู่ในสถานะรอรีวิว ให้เช็กตัวเลข
    if is_waiting_review(user_id) and user_text.strip() in ["1", "2", "3", "4", "5"]:
        set_review(user_id, int(user_text.strip()))
        send_message(chat_id, "✅ ขอบคุณสำหรับรีวิวครับ!")
        update_context(user_id, "review_done")
    else:
        send_message(chat_id, "ใช้คำสั่ง /review เพื่อให้คะแนน (1-5)")
