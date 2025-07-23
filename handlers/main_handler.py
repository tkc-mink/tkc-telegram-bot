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
from utils.message_utils import send_message  # สำหรับ fallback หรือ reply ทั่วไป

def handle_message(data):
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user_text = msg.get("caption", "") or msg.get("text", "")
    user_text = str(user_text or "").strip()
    user_text_low = user_text.lower()

    # Safety: ไม่ระบุ chat_id หรือไม่มี text/message เลย (ปล่อยผ่าน)
    if not chat_id:
        return

    try:
        # -- คำสั่ง command ต่างๆ --
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
        elif user_text_low.startswith("/start") or user_text_low.startswith("/help"):
            send_message(chat_id,
                "ยินดีต้อนรับสู่ TKC Bot 🦊\n\n"
                "- พิมพ์ /my_history ดูประวัติ\n"
                "- พิมพ์ /gold ราคาทอง\n"
                "- พิมพ์ /lottery ผลสลาก\n"
                "- พิมพ์ /weather อากาศ\n"
                "- พิมพ์ /review รีวิวบอท\n"
                "- ส่งเอกสาร (PDF, Excel, Word) เพื่อสรุป\n"
                "- หรือถามอะไรก็ได้..."
            )
        elif user_text.strip() == "":
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
        else:
            send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่อีกครั้ง หรือพิมพ์ /help")
    except Exception as e:
        send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
        # คุณสามารถเพิ่ม logging ได้ที่นี่ด้วย เช่น print(traceback.format_exc())
