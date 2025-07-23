# handlers/main_handler.py
import traceback
from typing import Dict, Any

# ---- Feature handlers (แยกไฟล์) ----
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
# from handlers.news import handle_news  # ถ้าทำข่าวเพิ่มค่อยเปิดใช้

# ---- Utils ----
from utils.message_utils import send_message
from utils.context_utils import update_location  # ใช้ตอนรับ location

def handle_message(data: Dict[str, Any]) -> None:
    """
    Entry point เรียกจาก Flask webhook
    data: raw dict จาก Telegram webhook
    """
    try:
        msg: Dict[str, Any] = data.get("message", {}) or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return  # ไม่ใช่ข้อความปกติ

        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # -------- PRIORITY: Document / Location --------
        # Document upload
        if msg.get("document"):
            handle_doc(chat_id, msg)
            return

        # Location share
        if msg.get("location"):
            loc = msg["location"]
            lat, lon = loc.get("latitude"), loc.get("longitude")
            if lat is not None and lon is not None:
                update_location(str(chat_id), lat, lon)
                send_message(chat_id, "✅ บันทึกตำแหน่งแล้ว! ลองถามอากาศอีกครั้งได้เลย")
            else:
                send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง กรุณาส่งใหม่")
            return

        # ไม่มีข้อความเลย
        if user_text == "":
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
            return

        # -------- COMMAND DISPATCH --------
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
        elif "ขอรูป" in user_text_low or user_text_low.startswith("/image"):
            handle_image(chat_id, user_text)
        elif user_text_low.startswith("/review"):
            handle_review(chat_id, user_text)
        # elif user_text_low.startswith("/news"):
        #     handle_news(chat_id, user_text)

        elif user_text_low.startswith("/start") or user_text_low.startswith("/help"):
            send_message(
                chat_id,
                "ยินดีต้อนรับสู่ TKC Bot 🦊\n\n"
                "- /my_history   ประวัติ 10 รายการล่าสุด\n"
                "- /gold         ราคาทองวันนี้\n"
                "- /lottery      ผลสลากกินแบ่ง\n"
                "- /stock <SYM>  ราคาหุ้น เช่น /stock AAPL\n"
                "- /crypto <SYM> ราคา Crypto เช่น /crypto BTC\n"
                "- /oil          ราคาน้ำมันโลก\n"
                "- /weather      สภาพอากาศ (ต้องแชร์ location ก่อน)\n"
                "- /review       ให้คะแนนบอท (1-5)\n"
                "- ส่งเอกสาร PDF/Word/Excel/PPT/TXT เพื่อสรุป\n"
                "- พิมพ์ 'ขอรูป ...' เพื่อค้นหารูปภาพ\n"
            )
        else:
            # Fallback
            send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่ หรือพิมพ์ /help")

    except Exception as e:
        # แจ้งผู้ใช้ + log
        try:
            send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
        except Exception:
            pass
        print("[MAIN_HANDLER ERROR]")
        print(traceback.format_exc())
