# handlers/review.py
from utils.message_utils import send_message
from utils.review_utils import set_review, need_review_today  # <== path

def handle_review(chat_id: int, user_text: str) -> None:
    user_id = str(chat_id)

    # ถ้าผู้ใช้พิมพ์ตัวเลขทันที
    txt = user_text.strip()
    if txt.isdigit() and txt in ["1","2","3","4","5"]:
        set_review(user_id, int(txt))
        send_message(chat_id, "✅ ขอบคุณสำหรับรีวิวครับ!")
        return

    # ถ้ายังไม่ได้รีวิววันนี้แต่มาเรียก /review
    if need_review_today(user_id):
        send_message(chat_id, "❓ กรุณารีวิววันนี้ (1-5):")
    else:
        send_message(chat_id, "วันนี้ไม่จำเป็นต้องรีวิวครับ")
