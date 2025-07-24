# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Dispatch ข้อความ/อีเวนต์จาก Telegram (ผ่าน Flask webhook) ไปยัง handler ย่อยแต่ละฟีเจอร์
"""
from typing import Dict, Any
import traceback

# ========= Feature Handlers =========
from handlers.history  import handle_history
from handlers.review   import handle_review
from handlers.weather  import handle_weather
from handlers.doc      import handle_doc
from handlers.image    import handle_image
from handlers.gold     import handle_gold
from handlers.lottery  import handle_lottery
from handlers.stock    import handle_stock
from handlers.crypto   import handle_crypto
from handlers.oil      import handle_oil
# from handlers.news     import handle_news # (ถ้ายังไม่มีไฟล์ อย่า import)

# ========= Utils =========
from utils.message_utils import send_message, ask_for_location
from utils.context_utils import update_location   # ใช้เมื่อผู้ใช้ส่ง location

# ========= AI Function Calling =========
from function_calling import process_with_function_calling

def handle_message(data: Dict[str, Any]) -> None:
    chat_id = None
    try:
        msg: Dict[str, Any] = data.get("message", {}) or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return

        # ---- แยกข้อมูลพื้นฐาน ----
        user_text: str = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # 1) Document
        if msg.get("document"):
            handle_doc(chat_id, msg)
            return

        # 2) Location
        if msg.get("location"):
            _handle_location_message(chat_id, msg)
            return

        # 3) ไม่มีข้อความ
        if not user_text:
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
            return

        # 4) Dispatch ตามคำสั่ง/คีย์เวิร์ด
        if user_text_low.startswith("/my_history"):
            handle_history(chat_id, user_text)

        elif user_text_low.startswith("/gold") or "ราคาทอง" in user_text_low:
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
            _send_help(chat_id)

        else:
            # ส่งข้อความทั่วไปให้ AI (GPT) ตอบกลับ
            reply = process_with_function_calling(user_text)
            send_message(chat_id, reply)

    except Exception as e:
        # ส่ง error ให้ผู้ใช้ (ถ้า chat_id ยังมี) และ log stacktrace
        if chat_id is not None:
            try:
                send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
            except Exception:
                pass
        print("[MAIN_HANDLER ERROR]")
        print(traceback.format_exc())

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _handle_location_message(chat_id: int, msg: Dict[str, Any]) -> None:
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        update_location(str(chat_id), lat, lon)
        send_message(chat_id, "✅ บันทึกตำแหน่งแล้ว! ลองถามอากาศอีกครั้งได้เลย (/weather)")
    else:
        send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง กรุณาส่งใหม่")

def _send_help(chat_id: int) -> None:
    send_message(
        chat_id,
        "ยินดีต้อนรับสู่ TKC Bot 🦊\n\n"
        "คำสั่งที่ใช้ได้:\n"
        "• /my_history   ดูประวัติคำถามย้อนหลัง 10 รายการ\n"
        "• /gold          ราคาทองคำวันนี้\n"
        "• /lottery       ผลสลากกินแบ่งรัฐบาลล่าสุด\n"
        "• /stock <SYM>   ราคาหุ้น เช่น /stock AAPL\n"
        "• /crypto <SYM>  ราคา Crypto เช่น /crypto BTC\n"
        "• /oil           ราคาน้ำมันโลก\n"
        "• /weather       สภาพอากาศ (ต้องแชร์ location ก่อนด้วยปุ่ม 📍)\n"
        "• /review        ให้คะแนนบอท (1-5)\n"
        "• ส่งเอกสาร PDF/Word/Excel/PPT/TXT เพื่อให้บอทช่วยสรุป\n"
        "• พิมพ์ 'ขอรูป ...' เพื่อให้บอทค้นหารูปภาพให้\n"
        "\nพิมพ์ /help ได้ตลอดเพื่อดูคำสั่ง"
    )
