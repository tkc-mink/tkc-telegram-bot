# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain) - Final Version with Correct Order
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
from handlers.favorite import handle_favorite
from handlers.admin import handle_admin_command

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
from utils.admin_utils import notify_super_admin_for_approval

# --- ✅ **ส่วนที่แก้ไข:** ย้าย Helper Functions ทั้งหมดมาไว้ก่อน COMMAND_HANDLERS ---

def _handle_start(user_info: Dict[str, Any], text: str):
    """Handles the /start command for existing, approved users."""
    chat_id = user_info['profile']['user_id']
    first_name = user_info['profile']['first_name']
    welcome_message = f"ยินดีต้อนรับกลับมาครับคุณ {first_name}! มีอะไรให้ 'ชิบะน้อย' รับใช้ไหมครับ"
    tg_send_message(chat_id, welcome_message)
    _send_help(chat_id)

def _handle_whoami(user_info: Dict[str, Any], text: str):
    """Responds with the bot's identity."""
    chat_id = user_info['profile']['user_id']
    tg_send_message(chat_id, bot_intro())

def _send_help(chat_id: int) -> None:
    """Sends a help message with a list of available commands."""
    help_text = (
        "**รายการคำสั่งที่ใช้ได้ครับ**\n\n"
        "• `/weather` - พยากรณ์อากาศ\n"
        "• `/stock <ชื่อหุ้น>` - ราคาหุ้น\n"
        "• `/gold` - ราคาทอง\n"
        "• `/news <หัวข้อ>` - ข่าวล่าสุด\n"
        "• `/review 5` - ให้คะแนนการทำงาน\n"
        "• `/favorite_list` - ดูรายการโปรด\n\n"
        "ผมยังมีความสามารถอื่นๆ อีกเยอะเลย ลองคุยกับผมได้เลยครับ!"
    )
    tg_send_message(chat_id, help_text, parse_mode="Markdown")

def _handle_location_message(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """Handles incoming location messages, saving them to the user's permanent profile."""
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

# ===== Command Router Configuration (ย้ายมาไว้ตรงนี้) =====
COMMAND_HANDLERS: Dict[str, Callable] = {
    # Commands starting with "/"
    "/my_history": handle_history, "/gold": handle_gold, "/lottery": handle_lottery,
    "/stock": handle_stock, "/crypto": handle_crypto, "/oil": handle_oil,
    "/weather": handle_weather, "/review": handle_review,
    "/report": handle_report, "/summary": handle_report,
    "/faq": handle_faq, "/add_faq": handle_faq, "/start": _handle_start,
    "/help": lambda ui, txt: _send_help(ui['profile']['user_id']),
    "/favorite": handle_favorite, "/favorite_add": handle_favorite, 
    "/favorite_list": handle_favorite, "/favorite_remove": handle_favorite,
    # Keyword-based commands
    "ราคาทอง": handle_gold, "อากาศ": handle_weather,
    "ชื่ออะไร": _handle_whoami, "คุณคือใคร": _handle_whoami,
}

# ===== Main Message Handling Logic =====
def handle_message(data: Dict[str, Any]) -> None:
    """The main entry point for processing all incoming messages."""
    chat_id = None
    try:
        msg = data.get("message") or data.get("edited_message") or {}
        if not msg: return

        chat_id = msg.get("chat", {}).get("id")
        user_data = msg.get("from")
        if not chat_id or not user_data: return

        user_info = get_or_create_user(user_data)
        if not user_info:
            tg_send_message(chat_id, "ขออภัยครับ ระบบความทรงจำของผมมีปัญหาชั่วคราว")
            return
        
        status = user_info['status']
        profile = user_info['profile']
        
        # --- User Approval Workflow ---
        if status == "new_user_pending":
            send_message(profile['user_id'], "สวัสดีครับ! คำขอเข้าใช้งานของคุณถูกส่งไปให้ผู้ดูแลระบบแล้ว กรุณารอการอนุมัติสักครู่นะครับ")
            notify_super_admin_for_approval(user_data)
            return
        if profile['status'] == 'pending':
            send_message(profile['user_id'], "บัญชีของคุณยังรอการอนุมัติจากผู้ดูแลระบบครับ")
            return
        if profile['status'] != 'approved':
            send_message(profile['user_id'], "บัญชีของคุณไม่ได้รับอนุญาตให้ใช้งานระบบครับ")
            return
        
        user_id = profile['user_id']
        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()
        
        # --- Admin Command Route ---
        if user_text_low.startswith('/admin'):
            return handle_admin_command(user_info, user_text)

        # --- Non-Text Message Routes ---
        if msg.get("document"): return handle_doc(user_info, msg)
        if msg.get("location"): return _handle_location_message(user_info, msg)
        
        if not user_text:
            tg_send_message(chat_id, "สวัสดีครับ มีอะไรให้ผมรับใช้ไหมครับ? พิมพ์ /help เพื่อดูคำสั่งได้เลยครับ")
            return

        # --- General Command Router ---
        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                return handler(user_info, user_text)

        # --- General Conversation (Function Calling) ---
        append_message(user_id, "user", user_text)
        ctx = get_recent_context(user_id)
        summary = get_summary(user_id)
        reply = process_with_function_calling(user_info, user_text, ctx=ctx, conv_summary=summary)
        tg_send_message(chat_id, reply)
        append_message(user_id, "assistant", reply)
        prune_and_maybe_summarize(user_id, summarize_func=summarize_text_with_gpt)

    except Exception as e:
        print(f"[MAIN_HANDLER ERROR] {e}\n{traceback.format_exc()}")
        if chat_id:
            tg_send_message(chat_id, f"ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล")
