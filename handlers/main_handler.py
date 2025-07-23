# handlers/main_handler.py

from handlers.history import handle_history
from handlers.review import handle_review
from handlers.weather import handle_weather
from handlers.doc import handle_doc
from handlers.image import handle_image
from handlers.gold import handle_gold
from handlers.lottery import handle_lottery
from handlers.stock import handle_stock
from handlers.crypto import handle_crypto
from handlers.oil import handle_oil
# ... import handler อื่นๆ

from utils.message_utils import send_message  # สำหรับ fallback หรือ reply ทั่วไป

def handle_message(data):
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user_text = msg.get("caption", "") or msg.get("text", "")

    if not chat_id or not user_text:
        return

    user_text_low = user_text.lower()

    # ตัวอย่าง dispatch ที่รองรับทั้ง /command และ keyword ภาษาไทย
    if user_text_low.startswith("/my_history"):
        handle_history(chat_id, user_text)
    elif user_text_low.startswith("/gold"):
        handle_gold(chat_id, user_text)
    elif user_text_low.startswith("/lottery"):
        handle_lottery(chat_id, user_text)
    elif user_text_low.startswith("/stock"):
        handle_stock(chat_id, user_text)
    elif user_text_low.startswith("/crypto"):
        handle_crypto(chat_id, user_text)
    elif user_text_low.startswith("/oil"):
        handle_oil(chat_id, user_text)
    elif user_text_low.startswith("/weather") or "อากาศ" in user_text_low:
        handle_weather(chat_id, user_text)
    elif "ขอรูป" in user_text_low or "/image" in user_text_low:
        handle_image(chat_id, user_text)
    elif user_text_low.startswith("/review"):
        handle_review(chat_id, user_text)
    elif user_text_low.startswith("/doc") or msg.get("document"):
        handle_doc(chat_id, msg)
    else:
        # fallback message: ตอบกลับถ้าไม่เข้าเงื่อนไขใดเลย
        send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่อีกครั้งหรือพิมพ์ /help")

