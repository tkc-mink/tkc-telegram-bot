# handlers/review.py
from utils.message_utils import send_message
from utils.review_utils import set_review, need_review_today
from utils.context_utils import update_context, is_waiting_review  # ถ้าไม่มีฟังก์ชันเหล่านี้ใน context_utils ให้ตัดออก

def handle_review(chat_id, user_text):
    """
    ให้คะแนนบอทแบบง่าย ๆ: ผู้ใช้พิมพ์ /review 1-5
    หรือถ้าคุณใช้ flow ถาม-ตอบหลายขั้น ให้แยก ConversationHandler (แต่ที่นี่เรียบง่าย)
    """
    parts = user_text.split()
    user_id = str(chat_id)

    # ถ้าผู้ใช้ส่งเลขมาเลย
    if len(parts) > 1 and parts[1].isdigit() and parts[1] in ["1","2","3","4","5"]:
        rating = int(parts[1])
        set_review(user_id, rating)
        send_message(chat_id, "✅ ขอบคุณสำหรับรีวิวครับ!")
        return

    # ถ้ายังไม่ได้ให้คะแนน แต่จำเป็นต้องรีวิว
    if need_review_today(user_id):
        send_message(chat_id, "❓ กรุณารีวิวความพึงพอใจ (1-5): เช่น /review 5")
    else:
        send_message(chat_id, "วันนี้ไม่จำเป็นต้องรีวิวครับ (หรือจะให้คะแนนก็พิมพ์ /review 1-5 ได้เลย)")
