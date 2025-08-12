# handlers/main_handler.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
import re
import traceback

# ===== Handler Imports (ส่วนที่ 1: คำสั่งดั้งเดิม) =====
from handlers.history       import handle_history
from handlers.review        import handle_review
from handlers.weather       import handle_weather
from handlers.doc           import handle_doc
from handlers.gold          import handle_gold
from handlers.lottery       import handle_lottery
from handlers.stock         import handle_stock
from handlers.crypto        import handle_crypto
from handlers.oil           import handle_oil
from handlers.report        import handle_report
from handlers.faq           import handle_faq
from handlers.backup_status import handle_backup_status

# ===== Handler Imports (ส่วนที่ 2: อัปเกรดเป็น Gemini) =====
# from handlers.search     import handle_Google Search, handle_google_image # << ปิดการใช้งานของเก่า
from handlers.search        import handle_gemini_search, handle_gemini_image_generation # ✅ เปิดใช้ Gemini
from handlers.image         import handle_image # (สำหรับวิเคราะห์ภาพที่ผู้ใช้ส่งมา)

# ===== Utility Imports =====
from utils.telegram_api import send_message as tg_send_message
from utils.context_utils import update_location
from function_calling import process_with_function_calling # (ส่วนนี้อาจจะต้องปรับไปใช้ Gemini ในอนาคต)
from utils.bot_profile import bot_intro, adjust_bot_tone

# ===== Memory Layer =====
from utils.memory_store import (
    append_message,
    get_recent_context,
    get_summary,
    prune_and_maybe_summarize,
)

# ... (ส่วน _sanitize_no_echo ของคุณเหมือนเดิม ไม่ต้องเปลี่ยนแปลง) ...

# -------------------------------------------------

def handle_message(data: Dict[str, Any]) -> None:
    chat_id = None
    try:
        msg: Dict[str, Any] = data.get("message") or data.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return
        user_id = str(chat_id)

        user_text: str = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.casefold()

        # 1) เอกสาร
        if msg.get("document"):
            print("[MAIN_HANDLER] dispatch: document")
            handle_doc(chat_id, msg)
            return

        # 2) ตำแหน่ง
        if msg.get("location"):
            print("[MAIN_HANDLER] dispatch: location")
            _handle_location_message(chat_id, msg)
            return

        # 3) สื่อ (ภาพ/วิดีโอที่ผู้ใช้ส่งมาเพื่อ "วิเคราะห์")
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            print("[MAIN_HANDLER] dispatch: media analysis")
            handle_image(chat_id, msg) # ใช้ handler เดิมสำหรับวิเคราะห์ภาพที่ส่งมา
            return

        # 4) ข้อความว่าง
        if not user_text:
            tg_send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ ส่งรูป หรือใช้ /help")
            return

        # 5) คำสั่ง (Routing Logic)
        if user_text_low.startswith("/my_history"):
            print("[MAIN_HANDLER] dispatch: /my_history"); handle_history(chat_id, user_text)

        elif user_text_low.startswith("/gold") or "ราคาทอง" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /gold"); handle_gold(chat_id, user_text)

        elif user_text_low.startswith("/lottery"):
            print("[MAIN_HANDLER] dispatch: /lottery"); handle_lottery(chat_id, user_text)

        elif user_text_low.startswith("/stock"):
            print("[MAIN_HANDLER] dispatch: /stock"); handle_stock(chat_id, user_text)

        elif user_text_low.startswith("/crypto"):
            print("[MAIN_HANDLER] dispatch: /crypto"); handle_crypto(chat_id, user_text)

        elif user_text_low.startswith("/oil"):
            print("[MAIN_HANDLER] dispatch: /oil"); handle_oil(chat_id, user_text)

        elif user_text_low.startswith("/weather") or "อากาศ" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /weather"); handle_weather(chat_id, user_text)

        # =================================================================
        #  ✅✅✅ --- SWITCH TO GEMINI --- ✅✅✅
        # =================================================================
        elif user_text_low.startswith("/search") or user_text_low.startswith("ค้นหา"):
            print("[MAIN_HANDLER] dispatch: /search (GEMINI)")
            handle_gemini_search(chat_id, user_text) # << เปลี่ยนมาเรียก Gemini Search

        elif (user_text_low.startswith("/image") or
              user_text_low.startswith("/imagine") or # เพิ่มคำสั่ง /imagine
              user_text_low.startswith("สร้างภาพ")):
            print("[MAIN_HANDLER] dispatch: /image (GEMINI)")
            handle_gemini_image_generation(chat_id, user_text) # << เปลี่ยนมาเรียก Gemini Image Gen
        # =================================================================

        elif user_text_low.startswith("/review"):
            print("[MAIN_HANDLER] dispatch: /review"); handle_review(chat_id, user_text)

        elif user_text_low.startswith("/backup_status") or "backup ล่าสุด" in user_text_low:
            print("[MAIN_HANDLER] dispatch: /backup_status"); handle_backup_status(chat_id, user_text)

        elif user_text_low.startswith("/report") or user_text_low.startswith("/summary"):
            print("[MAIN_HANDLER] dispatch: /report"); handle_report(chat_id, user_text)

        elif user_text_low.startswith("/faq") or user_text_low.startswith("/add_faq"):
            print("[MAIN_HANDLER] dispatch: /faq"); handle_faq(chat_id, user_text)

        elif user_text_low.startswith("/start") or user_text_low.startswith("/help"):
            print("[MAIN_HANDLER] dispatch: /start|/help")
            tg_send_message(chat_id, bot_intro())
            _send_help(chat_id)

        elif "ชื่ออะไร" in user_text_low or "คุณคือใคร" in user_text_low:
            print("[MAIN_HANDLER] dispatch: whoami")
            tg_send_message(chat_id, bot_intro())

        else:
            # 6) การตอบทั่วไป (ส่วนนี้ยังใช้ Function Calling เดิม)
            # ในอนาคตเราสามารถอัปเกรด process_with_function_calling ให้เรียกใช้ Gemini ได้เช่นกัน
            print("[MAIN_HANDLER] dispatch: function_calling (using old model for now)")
            ctx = get_recent_context(user_id)
            summary = get_summary(user_id)
            reply = process_with_function_calling(user_text, ctx=ctx, conv_summary=summary)
            reply = _sanitize_no_echo(user_text, reply)
            reply = adjust_bot_tone(reply)
            tg_send_message(chat_id, reply)
            append_message(user_id, "user", user_text)
            append_message(user_id, "assistant", reply)
            prune_and_maybe_summarize(user_id)

    except Exception as e:
        if chat_id is not None:
            try: tg_send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
            except Exception: pass
        print("[MAIN_HANDLER ERROR]"); print(traceback.format_exc())

# ... (ฟังก์ชัน _handle_location_message และ _send_help ของคุณเหมือนเดิม) ...

def _send_help(chat_id: int) -> None:
    tg_send_message(
        chat_id,
        "คำสั่งที่ใช้ได้:\n"
        "• /search <คำค้น>    ค้นหาและสรุปข้อมูลล่าสุดด้วย Gemini\n"
        "• /image <คำอธิบาย> สร้างภาพใหม่ด้วย Gemini\n"
        "---------------------\n"
        "• /my_history        ดูประวัติย้อนหลัง\n"
        "• /gold               ราคาทอง\n"
        "• /lottery            ผลสลากฯ\n"
        "• /stock <SYM>        ราคาหุ้น\n"
        "• /crypto <SYM>       ราคาเหรียญ\n"
        "• /oil                ราคาน้ำมัน\n"
        "• /weather            พยากรณ์อากาศ (แชร์ location)\n"
        "• /review             รีวิวบอท\n"
        "• /backup_status      เช็ก backup\n"
        "• /faq, /add_faq      จัดการคำถามที่พบบ่อย\n"
        "\nพิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
    )
