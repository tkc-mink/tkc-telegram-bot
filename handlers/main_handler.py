# handlers/main_handler.py
# -*- coding: utf-8 -*-
from typing import Dict, Any
import traceback

from handlers.history       import handle_history
from handlers.review        import handle_review
from handlers.weather       import handle_weather
from handlers.doc           import handle_doc
from handlers.image         import handle_image
from handlers.gold          import handle_gold
from handlers.lottery       import handle_lottery
from handlers.stock         import handle_stock
from handlers.crypto        import handle_crypto
from handlers.oil           import handle_oil
from handlers.search        import handle_google_search, handle_google_image
from handlers.report        import handle_report
from handlers.faq           import handle_faq
from handlers.backup_status import handle_backup_status

# >>> เปลี่ยนมาใช้ตัวส่งข้อความที่มีดีบักของเราโดยตรง
from utils.telegram_api import send_message as tg_send_message
# (ถ้าต้องใช้ helper อื่นใน message_utils ค่อย import รายตัวมาเพิ่มภายหลัง)

from utils.context_utils import update_location
from function_calling import process_with_function_calling
from utils.bot_profile import bot_intro, adjust_bot_tone

# จำว่าแต่ละ user แนะนำตัวไปแล้วหรือยัง (memory แบบง่าย)
user_intro: dict[int, bool] = {}


def handle_message(data: Dict[str, Any]) -> None:
    chat_id = None
    try:
        # รองรับทั้ง message และ edited_message (กันบางเคสที่ Telegram ส่งมา)
        msg: Dict[str, Any] = data.get("message") or data.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return

        # ดึงข้อความจาก text/caption (ถ้ามี)
        user_text: str = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # 1) ไฟล์เอกสาร -> ให้ handler doc จัดการ
        if msg.get("document"):
            print("[MAIN_HANDLER] dispatch: document")
            handle_doc(chat_id, msg)
            return

        # 2) ตำแหน่งที่ตั้ง
        if msg.get("location"):
            print("[MAIN_HANDLER] dispatch: location")
            _handle_location_message(chat_id, msg)
            return

        # 3) รูปภาพ/สื่อ
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            print("[MAIN_HANDLER] dispatch: media")
            handle_image(chat_id, msg)
            return

        # 4) ไม่มีข้อความและไม่มีสื่อ -> แจ้งช่วยเหลือ
        if not user_text:
            tg_send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ ส่งรูป หรือใช้ /help")
            return

        # == INTRO LOGIC ==
        intro_needed = False
        if user_text_low.startswith("/start") or not user_intro.get(chat_id):
            intro_needed = True
            user_intro[chat_id] = True  # จดว่าแนะนำตัวแล้ว

        # 5) Dispatch ตามคำสั่ง/คีย์เวิร์ด
        if user_text_low.startswith("/my_history"):
            print("[MAIN_HANDLER] dispatch: /my_history")
            handle_history(chat_id, user_text)

        elif user_text_low.startswith("/gold") or "ราคาทอง" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /gold")
            handle_gold(chat_id, user_text)

        elif user_text_low.startswith("/lottery"):
            print("[MAIN_HANDLER] dispatch: /lottery")
            handle_lottery(chat_id, user_text)

        elif user_text_low.startswith("/stock"):
            print("[MAIN_HANDLER] dispatch: /stock")
            handle_stock(chat_id, user_text)

        elif user_text_low.startswith("/crypto"):
            print("[MAIN_HANDLER] dispatch: /crypto")
            handle_crypto(chat_id, user_text)

        elif user_text_low.startswith("/oil"):
            print("[MAIN_HANDLER] dispatch: /oil")
            handle_oil(chat_id, user_text)

        elif user_text_low.startswith("/weather") or "อากาศ" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /weather")
            handle_weather(chat_id, user_text)

        elif user_text_low.startswith("/search") or user_text_low.startswith("ค้นหา"):
            print("[MAIN_HANDLER] dispatch: /search")
            handle_google_search(chat_id, user_text)

        elif user_text_low.startswith("/image") or "ขอรูป" in user_text_low or user_text_low.startswith("หารูป"):
            print("[MAIN_HANDLER] dispatch: /image")
            handle_google_image(chat_id, user_text)

        elif user_text_low.startswith("/review"):
            print("[MAIN_HANDLER] dispatch: /review")
            handle_review(chat_id, user_text)

        elif user_text_low.startswith("/backup_status") or "backup ล่าสุด" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /backup_status")
            handle_backup_status(chat_id, user_text)

        elif user_text_low.startswith("/report") or user_text_low.startswith("/summary"):
            print("[MAIN_HANDLER] dispatch: /report")
            handle_report(chat_id, user_text)

        elif user_text_low.startswith("/faq") or user_text_low.startswith("/add_faq"):
            print("[MAIN_HANDLER] dispatch: /faq")
            handle_faq(chat_id, user_text)

        elif user_text_low.startswith("/start") or user_text_low.startswith("/help"):
            print("[MAIN_HANDLER] dispatch: /start|/help")
            if intro_needed:
                tg_send_message(chat_id, bot_intro())
            _send_help(chat_id)

        elif "ชื่ออะไร" in user_text_low or "คุณคือใคร" in user_text_low:
            print("[MAIN_HANDLER] dispatch: whoami")
            tg_send_message(chat_id, bot_intro())

        elif user_text_low.startswith("/imagine"):
            print("[MAIN_HANDLER] dispatch: /imagine")
            pseudo_msg = {"text": user_text}
            handle_image(chat_id, pseudo_msg)

        else:
            # 6) ตอบแบบ AI/Function calling
            print("[MAIN_HANDLER] dispatch: function_calling")
            reply = process_with_function_calling(user_text)
            if intro_needed:
                reply = bot_intro() + "\n" + adjust_bot_tone(reply)
            else:
                reply = adjust_bot_tone(reply)
            tg_send_message(chat_id, reply)

    except Exception as e:
        if chat_id is not None:
            try:
                tg_send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
            except Exception:
                pass
        print("[MAIN_HANDLER ERROR]")
        print(traceback.format_exc())


def _handle_location_message(chat_id: int, msg: Dict[str, Any]) -> None:
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        update_location(str(chat_id), lat, lon)
        tg_send_message(chat_id, "✅ บันทึกตำแหน่งแล้ว! ลองถามอากาศอีกครั้งได้เลย (/weather)")
    else:
        tg_send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง กรุณาส่งใหม่")


def _send_help(chat_id: int) -> None:
    tg_send_message(
        chat_id,
        "คำสั่งที่ใช้ได้:\n"
        "• /my_history        ดูประวัติย้อนหลัง\n"
        "• /gold               ราคาทอง\n"
        "• /lottery            ผลสลากฯ\n"
        "• /stock <SYM>        ราคาหุ้น\n"
        "• /crypto <SYM>       ราคาเหรียญ\n"
        "• /oil                ราคาน้ำมัน\n"
        "• /weather            พยากรณ์อากาศ (แชร์ location)\n"
        "• /search             ค้นเว็บ Google\n"
        "• /image              ค้นหารูป Google\n"
        "• /imagine <prompt>   ให้บอทสร้างภาพ\n"
        "• /review             รีวิวบอท\n"
        "• /backup_status      เช็ก backup\n"
        "• /faq, /add_faq      จัดการคำถามที่พบบ่อย\n"
        "\nพิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
    )
