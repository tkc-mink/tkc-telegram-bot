# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
จุดรวมการ dispatch ข้อความจาก Telegram (ผ่าน Flask webhook -> handle_message)
เลือกส่งต่อไปยัง handler แต่ละฟีเจอร์ตามคำสั่ง / คีย์เวิร์ด
"""

from __future__ import annotations
import traceback
from typing import Dict, Any

# ===== Feature Handlers =====
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
# ถ้ามีข่าว ฯลฯ
# from handlers.news import handle_news

# ===== Utils =====
from utils.message_utils import send_message, ask_for_location
from utils.context_utils import update_location  # ใช้ตอนผู้ใช้ส่ง location

# -----------------------------------------------------------------------------

def handle_message(data: Dict[str, Any]) -> None:
    """
    Entry point เรียกจาก Flask webhook
    :param data: raw dict ที่ Telegram ส่งเข้ามา
    """
    chat_id = None
    try:
        msg: Dict[str, Any] = data.get("message", {}) or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            # ไม่ใช่ message ปกติ เช่น edited_message, callback_query ฯลฯ
            return

        # -------- แยกองค์ประกอบหลักจาก message --------
        user_text: str = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # ===== 1) ถ้าเป็นไฟล์เอกสาร -> ให้ doc handler จัดการทันที =====
        if msg.get("document"):
            handle_doc(chat_id, msg)
            return

        # ===== 2) ถ้าเป็นการแชร์ location =====
        if msg.get("location"):
            _handle_location_message(chat_id, msg)
            return

        # ===== 3) ถ้าไม่มีข้อความเลย =====
        if not user_text:
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
            return

        # ===== 4) Dispatch คำสั่ง =====
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
            _send_help(chat_id)

        else:
            # Fallback
            send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่ หรือพิมพ์ /help")

    except Exception as e:
        # แจ้งผู้ใช้ + log stacktrace
        if chat_id is not None:
            try:
                send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
            except Exception:
                pass
        print("[MAIN_HANDLER ERROR]")
        print(traceback.format_exc())

# -----------------------------------------------------------------------------
# Helpers ภายในไฟล์นี้
# -----------------------------------------------------------------------------

def _handle_location_message(chat_id: int, msg: Dict[str, Any]) -> None:
    """บันทึกตำแหน่งที่ผู้ใช้ส่งมา และแจ้งกลับ"""
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        update_location(str(chat_id), lat, lon)
        send_message(chat_id, "✅ บันทึกตำแหน่งแล้ว! ลองถามอากาศอีกครั้งได้เลย (/weather)")
    else:
        send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง กรุณาส่งใหม่")


def _send_help(chat_id: int) -> None:
    """ข้อความช่วยเหลือ/เมนู"""
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
        "• /weather       สภาพอากาศ (ต้องแชร์ location ก่อน, ใช้ปุ่ม 📍)\n"
        "• /review        ให้คะแนนบอท (1-5)\n"
        "• ส่งเอกสาร PDF/Word/Excel/PPT/TXT เพื่อให้บอทช่วยสรุป\n"
        "• พิมพ์ 'ขอรูป ...' เพื่อให้บอทค้นหารูปภาพให้\n"
    )
