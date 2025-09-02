# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain) - V3 (Admin & Approval Flow)
- Handles routing for all commands, including a dedicated admin route.
- Implements the user approval workflow.
"""
from __future__ import annotations
from typing import Dict, Any, Callable
import re
import traceback

# ===== Handler Imports =====
# (No changes here)
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
from handlers.favorite import handle_favorite
# ✅ 1. เพิ่ม import สำหรับพนักงานแอดมิน
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
# ✅ 2. เพิ่ม import สำหรับเครื่องมือแจ้งเตือนแอดมิน
from utils.admin_utils import notify_super_admin_for_approval

# (Helper functions _handle_start, _handle_whoami can remain the same)
# ...

# ===== Command Router Configuration =====
COMMAND_HANDLERS: Dict[str, Callable] = {
    # (No changes here, admin commands are handled separately now)
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

# (No-Echo Sanitizer can remain the same)
# ...

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
            print(f"[MAIN_HANDLER] Could not process user profile for {user_data.get('id')}")
            tg_send_message(chat_id, "ขออภัยครับ ระบบความทรงจำของผมมีปัญหาชั่วคราว กรุณาลองอีกครั้งภายหลังครับ")
            return
        
        # --- ✅ 3. **ตรรกะการอนุมัติผู้ใช้ใหม่** ---
        status = user_info['status']
        profile = user_info['profile']
        
        # ถ้าเป็นผู้ใช้ใหม่ที่เพิ่งถูกสร้างและกำลังรออนุมัติ
        if status == "new_user_pending":
            send_message(profile['user_id'], "สวัสดีครับ! คำขอเข้าใช้งานของคุณถูกส่งไปให้ผู้ดูแลระบบแล้ว กรุณารอการอนุมัติสักครู่นะครับ")
            notify_super_admin_for_approval(user_data)
            return

        # ถ้าเป็นผู้ใช้เก่าที่สถานะยังเป็น pending
        if profile['status'] == 'pending':
            send_message(profile['user_id'], "บัญชีของคุณยังรอการอนุมัติจากผู้ดูแลระบบครับ")
            return
            
        # ถ้าสถานะไม่ใช่ 'approved' (เช่น 'removed' หรืออื่นๆ)
        if profile['status'] != 'approved':
            send_message(profile['user_id'], "บัญชีของคุณไม่ได้รับอนุญาตให้ใช้งานระบบครับ")
            return
        # --- สิ้นสุดตรรกะการอนุมัติ ---
        
        user_id = user_info['profile']['user_id']
        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()
        
        # --- ✅ 4. **เพิ่ม Admin Command Router** ---
        # ตรวจสอบคำสั่งแอดมินก่อนคำสั่งทั่วไปเสมอ
        if user_text_low.startswith('/admin'):
            return handle_admin_command(user_info, user_text)

        # (ส่วนจัดการข้อความประเภทอื่นๆ เหมือนเดิม)
        if msg.get("document"): return handle_doc(user_info, msg)
        if msg.get("location"): return _handle_location_message(user_info, msg)
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            return handle_image(user_info, msg)
        if not user_text:
            tg_send_message(chat_id, "สวัสดีครับ มีอะไรให้ผมรับใช้ไหมครับ? พิมพ์ /help เพื่อดูคำสั่งได้เลยครับ")
            return

        # (ส่วน Command Router สำหรับผู้ใช้ทั่วไปเหมือนเดิม)
        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                return handler(user_info, user_text)

        # (ส่วนจัดการ General Conversation เหมือนเดิม)
        print(f"[MAIN_HANDLER] Dispatching to general conversation for user {user_id}")
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
            tg_send_message(chat_id, f"ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล: {e}")

# (ฟังก์ชัน _handle_location_message และ _send_help เหมือนเดิม)
# ...
