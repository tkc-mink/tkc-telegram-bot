# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain) - Final Version
- Fully integrated with all new utilities and the function calling engine.
"""
from __future__ import annotations
from typing import Dict, Any, Callable
import re
import traceback

# ===== Handler Imports =====
from handlers.history import handle_history
from handlers.review import handle_review
from handlers.weather import handle_weather
from handlers.doc import handle_doc
from handlers.gold import handle_gold
from handlers.lottery import handle_lottery
from handlers.stock import handle_stock
from handlers.crypto import handle_crypto
from handlers.oil import handle_oil
from handlers.report import handle_report
from handlers.faq import handle_faq
from handlers.backup_status import handle_backup_status
from handlers.search import handle_gemini_search, handle_gemini_image_generation
from handlers.image import handle_image
from handlers.favorite import handle_favorite # ✅ เพิ่ม favorite handler

# ===== Utility Imports =====
from utils.telegram_api import send_message as tg_send_message
from function_calling import process_with_function_calling, summarize_text_with_gpt
from utils.bot_profile import bot_intro
from utils.memory_store import (
    get_or_create_user,
    append_message,
    get_recent_context,
    get_summary,
    prune_and_maybe_summarize,
    update_user_location
)

# --- Helper Functions for Commands ---
def _handle_start(user_info: Dict[str, Any], text: str):
    chat_id = user_info['profile']['user_id']
    first_name = user_info['profile']['first_name']
    if user_info['status'] == 'new_user':
        welcome_message = f"สวัสดีครับคุณ {first_name}! ยินดีที่ได้รู้จักครับ ผมคือ TKC Assistant ผู้ช่วยส่วนตัวของคุณ"
    else:
        welcome_message = f"ยินดีต้อนรับกลับมาครับคุณ {first_name}! มีอะไรให้ผมรับใช้ไหมครับ"
    tg_send_message(chat_id, welcome_message)
    _send_help(chat_id)

def _handle_whoami(user_info: Dict[str, Any], text: str):
    chat_id = user_info['profile']['user_id']
    tg_send_message(chat_id, bot_intro())

# ===== Command Router Configuration =====
COMMAND_HANDLERS: Dict[str, Callable] = {
    "/my_history": handle_history, "/gold": handle_gold, "/lottery": handle_lottery,
    "/stock": handle_stock, "/crypto": handle_crypto, "/oil": handle_oil,
    "/weather": handle_weather, "/search": handle_gemini_search,
    "/image": handle_gemini_image_generation, "/imagine": handle_gemini_image_generation,
    "/review": handle_review, "/backup_status": handle_backup_status,
    "/report": handle_report, "/summary": handle_report,
    "/faq": handle_faq, "/add_faq": handle_faq, "/start": _handle_start,
    "/help": lambda ui, txt: _send_help(ui['profile']['user_id']),
    "/favorite": handle_favorite, "/favorite_add": handle_favorite, 
    "/favorite_list": handle_favorite, "/favorite_remove": handle_favorite,

    "ราคาทอง": handle_gold, "อากาศ": handle_weather, "ค้นหา": handle_gemini_search,
    "สร้างภาพ": handle_gemini_image_generation, "backup ล่าสุด": handle_backup_status,
    "ชื่ออะไร": _handle_whoami, "คุณคือใคร": _handle_whoami,
}

# (ส่วนของ No-Echo Sanitizer สามารถคงไว้เหมือนเดิม)

# ===== Main Message Handling Logic =====
def handle_message(data: Dict[str, Any]) -> None:
    chat_id = None
    try:
        msg = data.get("message") or data.get("edited_message") or {}
        if not msg: return

        chat_id = msg.get("chat", {}).get("id")
        user_data = msg.get("from")
        if not chat_id or not user_data: return

        user_info = get_or_create_user(user_data)
        if not user_info:
            print(f"[MAIN_HANDLER] Could not process user profile for {user_data.get('id')}")
            tg_send_message(chat_id, "ขออภัยครับ ระบบความทรงจำของผมมีปัญหาชั่วคราว กรุณาลองอีกครั้งภายหลังครับ")
            return
        
        user_id = user_info['profile']['user_id']
        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        if msg.get("document"): return handle_doc(user_info, msg)
        if msg.get("location"): return _handle_location_message(user_info, msg)
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            return handle_image(user_info, msg)
        if not user_text:
            tg_send_message(chat_id, "สวัสดีครับ มีอะไรให้ผมรับใช้ไหมครับ? พิมพ์ /help เพื่อดูคำสั่งได้เลยครับ")
            return

        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                return handler(user_info, user_text)

        print(f"[MAIN_HANDLER] Dispatching to general conversation for user {user_id}")
        append_message(user_id, "user", user_text)
        ctx = get_recent_context(user_id)
        summary = get_summary(user_id)
        
        # --- ✅ **ส่วนที่แก้ไข** ---
        # ส่ง user_info เข้าไปด้วยเพื่อให้ function_calling engine ทำงานได้ถูกต้อง
        reply = process_with_function_calling(user_info, user_text, ctx=ctx, conv_summary=summary)
        
        tg_send_message(chat_id, reply)
        append_message(user_id, "assistant", reply)
        prune_and_maybe_summarize(user_id, summarize_func=summarize_text_with_gpt)

    except Exception as e:
        print(f"[MAIN_HANDLER ERROR] {e}\n{traceback.format_exc()}")
        if chat_id:
            tg_send_message(chat_id, f"ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล: {e}")

# --- ✅ ฟังก์ชันที่อัปเกรดแล้ว ---
def _handle_location_message(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    user_id, chat_id, user_name = user_info['profile']['user_id'], user_info['profile']['user_id'], user_info['profile']['first_name']
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        if update_user_location(user_id, lat, lon):
            tg_send_message(chat_id, f"✅ ขอบคุณครับคุณ {user_name}! ผมบันทึกตำแหน่งของคุณแล้ว ลองใช้ /weather ได้เลยครับ")
        else:
            tg_send_message(chat_id, "❌ ขออภัยครับ เกิดปัญหาในการบันทึกตำแหน่ง")
    else:
        tg_send_message(chat_id, "❌ ตำแหน่งที่ส่งมาไม่ถูกต้อง")

def _send_help(chat_id: int) -> None:
    """Sends a help message with a list of available commands."""
    help_text = (
        "**รายการคำสั่งที่ใช้ได้ครับ**\n\n"
        "**ความสามารถหลัก:**\n"
        "• `/search <คำค้น>` - ค้นหาและสรุปข้อมูลล่าสุด\n"
        "• `/image <คำอธิบาย>` - สร้างภาพใหม่ตามจินตนาการ\n"
        "---------------------\n"
        "**เครื่องมืออื่นๆ:**\n"
        "• `/gold` - ราคาทอง\n"
        "• `/lottery` - ผลสลากฯ\n"
        "• `/stock <ชื่อหุ้น>` - ราคาหุ้น\n"
        "• `/crypto <ชื่อเหรียญ>` - ราคาเหรียญดิจิทัล\n"
        "• `/oil` - ราคาน้ำมัน\n"
        "• `/weather` - พยากรณ์อากาศ\n"
        "• `/review` - รีวิวการทำงานของผม\n"
        "• `/favorite_list` - ดูรายการโปรด\n\n"
        "*คุณสามารถพิมพ์คุยกับผมได้เลยทุกเรื่องนะครับ ผมจำได้ว่าเราคุยอะไรกันไว้บ้าง*"
    )
    tg_send_message(chat_id, help_text, parse_mode="Markdown")
