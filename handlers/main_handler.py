# handlers/main_handler.py
# -*- coding: utf-8 -*-
"""
Main Message Handler (The Bot's Brain) — FINAL, stable & backward-compatible
- แก้ NameError: ใช้ tg_send_message และทำ alias เป็น send_message
- กันประมวลผลซ้ำด้วย update_id (dedupe ในตัว; ถ้ามี utils.dedupe จะใช้ของเดิมอัตโนมัติ)
- คงฟีเจอร์เดิมทั้งหมด: history/review/weather/doc/gold/lottery/stock/crypto/oil/report/faq/favorite/admin
- รองรับข้อความ location, document และคำสั่ง /start, /help, /whoami (ชื่ออะไร/คุณคือใคร)
"""

from __future__ import annotations
from typing import Dict, Any, Callable
import time
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
from utils.telegram_api import send_message as tg_send_message  # ชื่อมาตรฐาน
# ทำ alias เพื่อ backward-compat กรณีโค้ดที่อื่นยังเรียก send_message
send_message = tg_send_message

from function_calling import process_with_function_calling, summarize_text_with_gpt
from utils.bot_profile import bot_intro
from utils.memory_store import (
    get_or_create_user,
    append_message,
    get_recent_context,
    get_summary,
    prune_and_maybe_summarize,
    update_user_location,
)
from utils.admin_utils import notify_super_admin_for_approval

# ===== Optional external dedupe support =====
# ถ้าโปรเจกต์มี utils.dedupe.seen_update อยู่แล้ว จะใช้ของเดิม
# ถ้าไม่มี เราจะใช้ตัวในไฟล์นี้ (LRU แบบง่าย TTL 10 นาที)
try:
    from utils.dedupe import seen_update as _ext_seen_update  # type: ignore
except Exception:  # pragma: no cover
    _ext_seen_update = None

# --- In-file dedupe (fallback) ---
_RECENT_UPDATES: dict[int, float] = {}
_DEDUPE_TTL_SEC = 600  # 10 นาที


def _seen_update(update_id: int) -> bool:
    """return True ถ้าเคยเห็น update_id ใน TTL; False ถ้ายังไม่เคย"""
    if _ext_seen_update:
        try:
            return _ext_seen_update(update_id)  # ใช้ของโปรเจกต์ถ้ามี
        except Exception:
            # หากของเดิมพัง ให้ตกกลับมาใช้ in-file dedupe
            pass

    now = time.time()
    # ล้างของหมดอายุ (ทำแบบขี้เกียจแต่พอเพียง)
    for k, ts in list(_RECENT_UPDATES.items()):
        if now - ts > _DEDUPE_TTL_SEC:
            _RECENT_UPDATES.pop(k, None)

    if update_id in _RECENT_UPDATES:
        return True
    _RECENT_UPDATES[update_id] = now
    return False


# ===== Helper Functions =====
def _send_help(chat_id: int) -> None:
    text = (
        "**รายการคำสั่งที่ใช้ได้ครับ**\n\n"
        "• `/weather` — พยากรณ์อากาศ\n"
        "• `/stock <ชื่อหุ้น>` — ราคาหุ้น\n"
        "• `/gold` — ราคาทอง\n"
        "• `/lottery` — ผลสลาก\n"
        "• `/crypto <เหรียญ>` — ราคา Crypto\n"
        "• `/oil` — ราคาน้ำมัน\n"
        "• `/review 1..5` — ให้คะแนนการทำงานของบอท\n"
        "• `/favorite_list` — ดูรายการโปรด\n"
        "• `/report` / `/summary` — สรุปภาพรวมการใช้งาน\n\n"
        "พิมพ์คุยธรรมดาได้เลย ผมจะพยายามช่วยเต็มที่ครับ!"
    )
    tg_send_message(chat_id, text, parse_mode="Markdown")


def _handle_start(user_info: Dict[str, Any], text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    first_name = user_info["profile"].get("first_name") or ""
    tg_send_message(chat_id, f"ยินดีต้อนรับกลับมาครับคุณ {first_name}! มีอะไรให้ 'ชิบะน้อย' รับใช้ไหมครับ")
    _send_help(chat_id)


def _handle_whoami(user_info: Dict[str, Any], text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    tg_send_message(chat_id, bot_intro())


def _handle_location_message(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """บันทึกพิกัดลงโปรไฟล์ถาวร แล้วชวนใช้ /weather"""
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""
    loc = msg.get("location") or {}
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is None or lon is None:
        tg_send_message(chat_id, "❌ ตำแหน่งที่ส่งมาไม่ถูกต้อง")
        return
    ok = update_user_location(chat_id, float(lat), float(lon))
    if ok:
        tg_send_message(chat_id, f"✅ ขอบคุณครับคุณ {user_name}! ผมบันทึกตำแหน่งของคุณแล้ว ลองใช้ /weather ได้เลยครับ")
    else:
        tg_send_message(chat_id, "❌ ขออภัยครับ เกิดปัญหาในการบันทึกตำแหน่ง")


# ===== Command Router =====
COMMAND_HANDLERS: Dict[str, Callable[[Dict[str, Any], str], Any]] = {
    # Slash commands
    "/start": _handle_start,
    "/help": lambda ui, txt: _send_help(ui["profile"]["user_id"]),
    "/my_history": handle_history,
    "/gold": handle_gold,
    "/lottery": handle_lottery,
    "/stock": handle_stock,
    "/crypto": handle_crypto,
    "/oil": handle_oil,
    "/weather": handle_weather,
    "/review": handle_review,
    "/report": handle_report,
    "/summary": handle_report,
    "/faq": handle_faq,
    "/add_faq": handle_faq,
    "/favorite": handle_favorite,
    "/favorite_add": handle_favorite,
    "/favorite_list": handle_favorite,
    "/favorite_remove": handle_favorite,
    # Phrase triggers (ภาษาไทย)
    "ราคาทอง": handle_gold,
    "อากาศ": handle_weather,
    "ชื่ออะไร": _handle_whoami,
    "คุณคือใคร": _handle_whoami,
}


# ===== Main Entry =====
def handle_message(data: Dict[str, Any]) -> None:
    """
    จุดเข้าใช้งานจาก Flask webhook (main.py)
    - ปลอดภัยต่อการ retry: มี dedupe ด้วย update_id
    - เสถียร: แยกเส้นทาง admin/location/document/command ก่อนลงโมเดล
    """
    chat_id = None
    try:
        # --- ตรวจโครงสร้างและกันซ้ำ ---
        upd = data.get("update_id")
        if isinstance(upd, int) and _seen_update(upd):
            return  # ข้าม update เดิมที่ Telegram retry

        msg = data.get("message") or data.get("edited_message") or {}
        if not msg:
            return

        chat_id = msg.get("chat", {}).get("id")
        user_data = msg.get("from") or {}
        if not chat_id or not user_data:
            return

        # --- สร้าง/โหลดโปรไฟล์ผู้ใช้ ---
        user_info = get_or_create_user(user_data)
        if not user_info:
            tg_send_message(chat_id, "ขออภัยครับ ระบบความทรงจำของผมมีปัญหาชั่วคราว")
            return

        profile = user_info.get("profile", {})
        status_top = user_info.get("status")               # ชั้นบนสุด (เดิม)
        status_prof = profile.get("status")                # ในโปรไฟล์

        # --- ขั้นอนุมัติผู้ใช้ใหม่ ---
        if status_top == "new_user_pending" or status_prof == "pending":
            tg_send_message(chat_id, "สวัสดีครับ! คำขอเข้าใช้งานของคุณถูกส่งให้ผู้ดูแลแล้ว กรุณารอสักครู่ครับ")
            # แจ้งผู้ดูแล (อย่าบล็อคเธรดนาน)
            try:
                notify_super_admin_for_approval(user_data)
            except Exception:
                traceback.print_exc()
            return

        if status_prof not in (None, "approved") and status_prof != "approved":
            tg_send_message(chat_id, "บัญชีของคุณไม่ได้รับอนุญาตให้ใช้งานระบบครับ")
            return

        user_id = profile.get("user_id") or chat_id
        user_text = (msg.get("caption") or msg.get("text") or "").strip()
        user_text_low = user_text.lower()

        # --- เส้นทางคำสั่ง admin ---
        if user_text_low.startswith("/admin"):
            return handle_admin_command(user_info, user_text)

        # --- เส้นทาง non-text ---
        if msg.get("document"):
            return handle_doc(user_info, msg)
        if msg.get("location"):
            return _handle_location_message(user_info, msg)

        if not user_text:
            tg_send_message(chat_id, "สวัสดีครับ มีอะไรให้ผมรับใช้ไหมครับ? พิมพ์ /help เพื่อดูคำสั่งได้เลยครับ")
            return

        # --- Router คำสั่งทั่วไป ---
        for command, handler in COMMAND_HANDLERS.items():
            if user_text_low.startswith(command):
                return handler(user_info, user_text)

        # --- โหมดสนทนาทั่วไป (Function Calling) ---
        append_message(user_id, "user", user_text)
        ctx = get_recent_context(user_id)
        summary = get_summary(user_id)
        try:
            reply = process_with_function_calling(
                user_info,
                user_text,
                ctx=ctx,
                conv_summary=summary,
            )
        except Exception:
            traceback.print_exc()
            reply = "ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล"

        tg_send_message(chat_id, reply)
        append_message(user_id, "assistant", reply)

        # จัดการบริบทและสรุปย่อเพื่อไม่ให้โตเกิน
        try:
            prune_and_maybe_summarize(user_id, summarize_func=summarize_text_with_gpt)
        except Exception:
            traceback.print_exc()

    except Exception as e:
        # ไม่เผยรายละเอียด error ให้ผู้ใช้ แต่ log เต็มใน Render
        print(f"[MAIN_HANDLER ERROR] {e}\n{traceback.format_exc()}")
        if chat_id:
            tg_send_message(chat_id, "ขออภัยครับ ผมเจอปัญหาบางอย่างในการประมวลผล")
