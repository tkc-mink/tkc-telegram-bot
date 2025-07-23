# handlers/main_handler.py
import traceback

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

from utils.message_utils import send_message  # fallback

def handle_message(data: dict) -> None:
    msg = data.get("message", {}) or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("caption") or msg.get("text") or "").strip()
    t = text.lower()

    if not chat_id:
        return

    try:
        if t.startswith("/my_history"):
            handle_history(chat_id, text)
        elif t.startswith("/gold"):
            handle_gold(chat_id, text)
        elif t.startswith("/lottery"):
            handle_lottery(chat_id, text)
        elif t.startswith("/stock"):
            handle_stock(chat_id, text)
        elif t.startswith("/crypto"):
            handle_crypto(chat_id, text)
        elif t.startswith("/oil"):
            handle_oil(chat_id, text)
        elif t.startswith("/weather") or "อากาศ" in t:
            handle_weather(chat_id, text)
        elif "ขอรูป" in t or t.startswith("/image"):
            handle_image(chat_id, text)
        elif t.startswith("/review"):
            handle_review(chat_id, text)
        elif t.startswith("/doc") or msg.get("document"):
            handle_doc(chat_id, msg)
        elif t.startswith("/start") or t.startswith("/help"):
            send_message(chat_id,
                "ยินดีต้อนรับสู่ TKC Bot 🦊\n\n"
                "- /my_history ดูประวัติ\n"
                "- /gold ราคาทอง\n"
                "- /lottery ผลสลาก\n"
                "- /stock หุ้น  /crypto คริปโต  /oil น้ำมัน\n"
                "- /weather อากาศ (ต้องแชร์ตำแหน่งก่อน)\n"
                "- /review รีวิวบอท\n"
                "- ส่งเอกสาร (PDF/Word/Excel/PPTX/TXT) เพื่อสรุป\n"
                "- พิมพ์ /help เพื่อดูคำสั่งอีกครั้ง"
            )
        elif text == "":
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
        else:
            send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่อีกครั้ง หรือพิมพ์ /help")
    except Exception as e:
        send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
        print("[HANDLE_MESSAGE ERROR]", traceback.format_exc())
