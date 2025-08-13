# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain) - Upgraded with Persistent Memory
This module acts as the central router for all incoming messages.
It now identifies users, greets them personally, and remembers conversations.
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

# --- ส่วนที่เราแก้ไข ---
# 1. เปลี่ยน import จาก memory_store ให้เป็นฟังก์ชันใหม่ที่เราสร้างขึ้น
from utils.memory_store import (
    get_or_create_user,
    append_message,
    get_recent_context,
    get_summary,
    prune_and_maybe_summarize,
)
# --------------------


def _handle_start(user_info: Dict[str, Any]):
    """Handles the /start command with a personalized greeting."""
    chat_id = user_info['profile']['user_id']
    first_name = user_info['profile']['first_name']

    if user_info['status'] == 'new_user':
        welcome_message = f"สวัสดีครับคุณ {first_name}! ยินดีที่ได้รู้จักครับ ผมคือ TKC Assistant ผู้ช่วยส่วนตัวของคุณ"
    else:
        welcome_message = f"ยินดีต้อนรับกลับมาครับคุณ {first_name}! มีอะไรให้ผมรับใช้ไหมครับ"

    tg_send_message(chat_id, welcome_message)
    _send_help(chat_id)

def _handle_whoami(user_info: Dict[str, Any]):
    """Responds with the bot's identity."""
    chat_id = user_info['profile']['user_id']
    tg_send_message(chat_id, bot_intro()) # bot_intro() ควรถูกแก้ไขให้เป็นกลางขึ้น

# ===== Command Router Configuration =====
# ✅ Refactor: ใช้ Dictionary Router แทน if/elif เพื่อความสะอาดและง่ายต่อการขยาย
# เราจะเรียกใช้ router นี้หลังจากที่ได้ user_info แล้ว
COMMAND_HANDLERS: Dict[str, Callable] = {
    "/my_history": handle_history,
    "/gold": handle_gold,
    "/lottery": handle_lottery,
    "/stock": handle_stock,
    "/crypto": handle_crypto,
    "/oil": handle_oil,
    "/weather": handle_weather,
    "/search": handle_gemini_search,
    "/image": handle_gemini_image_generation,
    "/imagine": handle_gemini_image_generation,
    "/review": handle_review,
    "/backup_status": handle_backup_status,
    "/report": handle_report,
    "/summary": handle_report,
    "/faq": handle_faq,
    "/add_faq": handle_faq,
    # คำสั่งที่ต้องการ user_info
    "/start": lambda user_info, text: _handle_start(user_info),
    "/help": lambda user_info, text: _send_help(user_info['profile']['user_id']),
    # Keyword-based commands
    "ราคาทอง": lambda user_info, text: handle_gold(user_info['profile']['user_id'], text),
    "อากาศ": lambda user_info, text: handle_weather(user_info['profile']['user_id'], text),
    "ค้นหา": lambda user_info, text: handle_gemini_search(user_info['profile']['user_id'], text),
    "สร้างภาพ": lambda user_info, text: handle_gemini_image_generation(user_info['profile']['user_id'], text),
    "backup ล่าสุด": lambda user_info, text: handle_backup_status(user_info['profile']['user_id'], text),
    "ชื่ออะไร": _handle_whoami,
    "คุณคือใคร": _handle_whoami,
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
    user_id = None
    try:
        msg = data.get("message") or data.get("edited_message") or {}
        if not msg: return # ถ้าไม่มี message object เลย ก็ไม่ต้องทำอะไร

        chat_id = msg.get("chat", {}).get("id")
        user_data = msg.get("from") # `from` field contains the user info

        if not chat_id or not user_data:
            print("[MAIN_HANDLER] No chat_id or user_data found.")
            return

        # --- ส่วนที่เราแก้ไข ---
        # 2. หัวใจของการจดจำ: เรียกใช้ get_or_create_user ทันที
        user_info = get_or_create_user(user_data)
        if not user_info:
            # กรณีฐานข้อมูลมีปัญหา, ส่งข้อความแจ้งผู้ใช้และหยุดทำงาน
            print(f"[MAIN_HANDLER] Could not get or create user profile for {user_data.get('id')}")
            tg_send_message(chat_id, "ขออภัยครับ ระบบความทรงจำของผมมีปัญหาชั่วคราว กรุณาลองอีกครั้งภายหลังครับ")
            return
        
        user_id = user_info['profile']['user_id']
        # --------------------

        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # --- Step 1: Handle Non-Text Messages First ---
        if msg.get("document"):
            return handle_doc(chat_id, msg) # ต้องปรับ handle_doc ให้รับ user_info แทน chat_id
        if msg.get("location"):
            return _handle_location_message(user_info, msg)
        if msg.get("photo") or msg.get("sticker") or msg.get("video") or msg.get("animation"):
            return handle_image(chat_id, msg) # ต้องปรับ handle_image ให้รับ user_info แทน chat_id
        if not user_text:
            # 3. เปลี่ยนคำตอบให้เป็นกลางขึ้น
            tg_send_message(chat_id, "สวัสดีครับ มีอะไรให้ผมรับใช้ไหมครับ? พิมพ์ข้อความ, ส่งรูป, หรือใช้ /help เพื่อดูคำสั่งทั้งหมดได้เลยครับ")
            return

        # --- Step 2: Check for Specific Commands using the Router ---
        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                print(f"[MAIN_HANDLER] Dispatching to: {handler.__name__} for command '{command}'")
                # 4. ส่ง user_info ทั้งก้อนไปให้ handler
                return handler(user_info, user_text)

        # --- Step 3: If no command matches, handle as a general conversation ---
        print(f"[MAIN_HANDLER] Dispatching to general conversation for user {user_id}")
        
        # 5. บันทึกข้อความของผู้ใช้ลงในความทรงจำถาวรทันที
        append_message(user_id, "user", user_text)

        ctx = get_recent_context(user_id)
        summary = get_summary(user_id)

        reply = process_with_function_calling(user_text, ctx=ctx, conv_summary=summary)
        
        reply = _sanitize_no_echo(user_text, reply)
        # เราอาจจะไม่ต้องใช้ adjust_bot_tone แล้ว ถ้า prompt ของเราดีพอ
        # reply = adjust_bot_tone(reply) 

        tg_send_message(chat_id, reply)

        # 6. บันทึกคำตอบของบอท และทำการสรุปถ้าจำเป็น
        append_message(user_id, "assistant", reply)
        prune_and_maybe_summarize(user_id, summarize_func=summarize_text_with_gpt)

    except Exception as e:
        print(f"[MAIN_HANDLER ERROR] {e}\n{traceback.format_exc()}")
        if chat_id:
            try:
                tg_send_message(chat_id, f"ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล: {e}")
            except Exception:
                pass

def _handle_location_message(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    user_id = user_info['profile']['user_id']
    chat_id = user_info['profile']['user_id'] # ในบริบทนี้ chat_id คือ user_id
    loc = msg.get("location", {})
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        update_location(str(user_id), lat, lon) # context_utils อาจต้องใช้ user_id ที่เป็น string
        tg_send_message(chat_id, "✅ ผมบันทึกตำแหน่งของคุณแล้วครับ! ลองถาม 'อากาศเป็นยังไง' ได้เลย")
    else:
        tg_send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง ลองส่งใหม่นะครับ")

def _send_help(chat_id: int) -> None:
    # 7. ปรับข้อความช่วยเหลือให้เป็นกลางและตรงกับความสามารถใหม่
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
        "• `/weather` - พยากรณ์อากาศ (ต้องแชร์ Location ก่อน)\n"
        "• `/review` - รีวิวการทำงานของผม\n"
        "\n*คุณสามารถพิมพ์คุยกับผมได้เลยทุกเรื่องนะครับ ผมจำได้ว่าเราคุยอะไรกันไว้บ้าง*"
    )
    tg_send_message(chat_id, help_text, parse_mode="Markdown")
