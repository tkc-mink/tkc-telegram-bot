# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain)
This module acts as the central router for all incoming messages.
It determines the message type and dispatches it to the appropriate handler.
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

# ===== Utility Imports =====
from utils.telegram_api import send_message as tg_send_message
from utils.context_utils import update_location
from function_calling import process_with_function_calling, summarize_text_with_gpt
from utils.bot_profile import bot_intro, adjust_bot_tone
from utils.memory_store import (
    append_message,
    get_recent_context,
    get_summary,
    prune_and_maybe_summarize,
)

# ===== Command Router Configuration =====
# ✅ Refactor: ใช้ Dictionary Router แทน if/elif เพื่อความสะอาดและง่ายต่อการขยาย
COMMAND_HANDLERS: Dict[str, Callable] = {
    # Commands starting with "/"
    "/my_history": handle_history,
    "/gold": handle_gold,
    "/lottery": handle_lottery,
    "/stock": handle_stock,
    "/crypto": handle_crypto,
    "/oil": handle_oil,
    "/weather": handle_weather,
    "/search": handle_gemini_search,
    "/image": handle_gemini_image_generation,
    "/imagine": handle_gemini_image_generation, # Alias for /image
    "/review": handle_review,
    "/backup_status": handle_backup_status,
    "/report": handle_report,
    "/summary": handle_report, # Alias for /report
    "/faq": handle_faq,
    "/add_faq": handle_faq,
    "/start": lambda chat_id, text: (tg_send_message(chat_id, bot_intro()), _send_help(chat_id)),
    "/help": lambda chat_id, text: _send_help(chat_id),
    # Keyword-based commands
    "ราคาทอง": handle_gold,
    "อากาศ": handle_weather,
    "ค้นหา": handle_gemini_search,
    "สร้างภาพ": handle_gemini_image_generation,
    "backup ล่าสุด": handle_backup_status,
    "ชื่ออะไร": lambda chat_id, text: tg_send_message(chat_id, bot_intro()),
    "คุณคือใคร": lambda chat_id, text: tg_send_message(chat_id, bot_intro()),
}

# ... (ส่วนของ No-Echo Sanitizer เหมือนเดิมทุกประการ) ...
_PREFIX_PATTERNS = [r"^\s*รับทราบ[:：-]\s*",r"^\s*คุณ\s*ถามว่า[:：-]\s*",r"^\s*สรุปคำถาม[:：-]\s*",r"^\s*ยืนยันคำถาม[:：-]\s*",r"^\s*คำถามของคุณ[:：-]\s*",r"^\s*Question[:：-]\s*",r"^\s*You\s+asked[:：-]\s*",]
_PREFIX_REGEX = re.compile("|".join(_PREFIX_PATTERNS), re.IGNORECASE | re.UNICODE)
def _strip_known_prefixes(text: str) -> str: return _PREFIX_REGEX.sub("", text or "", count=1)
def _looks_like_echo(user_text: str, line: str) -> bool:
    if not user_text or not line: return False
    def _norm(s: str) -> str:
        s = re.sub(r"[\"'`“”‘’\s]+", "", s, flags=re.UNICODE)
        s = re.sub(r"[.。…]+$", "", s, flags=re.UNICODE)
        return s.casefold()
    u = _norm(user_text); l = _norm(line)
    if not u or not l: return False
    if l.startswith(u[: max(1, int(len(u) * 0.85)) ]): return True
    if re.match(r'^\s*[>"`“‘]+', line): return True
    return False
def _sanitize_no_echo(user_text: str, reply: str) -> str:
    if not reply: return reply
    reply = _strip_known_prefixes(reply).lstrip()
    lines = reply.splitlines()
    if not lines: return reply
    if _looks_like_echo(user_text, lines[0]):
        lines = lines[1:]
        if lines: lines[0] = _strip_known_prefixes(lines[0]).lstrip()
    return ("\n".join(line.rstrip() for line in lines)).strip() or reply.strip()

# ===== Main Message Handling Logic =====
def handle_message(data: Dict[str, Any]) -> None:
    """The main entry point for processing incoming messages from Telegram."""
    chat_id = None
    try:
        msg = data.get("message") or data.get("edited_message") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return

        user_id = str(chat_id)
        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # --- Step 1: Handle Non-Text Messages First ---
        if msg.get("document"):
            return handle_doc(chat_id, msg)
        if msg.get("location"):
            return _handle_location_message(chat_id, msg)
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            return handle_image(chat_id, msg) # For vision analysis
        if not user_text:
            return tg_send_message(chat_id, "ชิบะน้อยรอรับคำสั่งอยู่ครับ! พิมพ์ข้อความ, ส่งรูป, หรือใช้ /help ได้เลยครับ 🐾")

        # --- Step 2: Check for Specific Commands using the Router ---
        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                print(f"[MAIN_HANDLER] Dispatching to: {handler.__name__} for command '{command}'")
                return handler(chat_id, user_text)

        # --- Step 3: If no command matches, handle as a general conversation ---
        print("[MAIN_HANDLER] Dispatching to general conversation (Function Calling)")
        ctx = get_recent_context(user_id)
        summary = get_summary(user_id)

        # Call the main Gemini-powered processing function
        reply = process_with_function_calling(user_text, ctx=ctx, conv_summary=summary)

        # Sanitize and adjust tone (though Gemini is generally good at this)
        reply = _sanitize_no_echo(user_text, reply)
        reply = adjust_bot_tone(reply) # Ensure "ชิบะน้อย" personality is consistent

        tg_send_message(chat_id, reply)

        # Update conversation memory
        append_message(user_id, "user", user_text)
        append_message(user_id, "assistant", reply)
        prune_and_maybe_summarize(user_id, summarize_func=summarize_text_with_gpt)

    except Exception as e:
        print(f"[MAIN_HANDLER ERROR] {e}\n{traceback.format_exc()}")
        if chat_id:
            try:
                tg_send_message(chat_id, f"โฮ่ง! ชิบะน้อยเจอปัญหาบางอย่างครับ: {e}")
            except Exception:
                pass

# ... (ส่วนของ _handle_location_message และ _send_help เหมือนเดิม) ...
def _handle_location_message(chat_id: int, msg: Dict[str, Any]) -> None:
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        update_location(str(chat_id), lat, lon)
        tg_send_message(chat_id, "✅ ชิบะน้อยบันทึกตำแหน่งแล้วครับ! ลองถามสภาพอากาศได้เลย (/weather)")
    else:
        tg_send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง ลองส่งใหม่นะครับ")

def _send_help(chat_id: int) -> None:
    help_text = (
        "🐾 **คำสั่งของชิบะน้อยครับ** 🐾\n\n"
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
        "• `/weather` - พยากรณ์อากาศ (ต้องแชร์ Location ก่อน)\n"
        "• `/review` - รีวิวการทำงานของชิบะน้อย\n"
        "\n*แค่พิมพ์คุยกับชิบะน้อยได้เลยทุกเรื่องนะครับ!*"
    )
    tg_send_message(chat_id, help_text, parse_mode="Markdown")
