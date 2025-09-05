# handlers/favorite_handlers.py
# -*- coding: utf-8 -*-
"""
ฟังก์ชันจัดการ 'รายการโปรด' ด้วย python-telegram-bot (async)
คำสั่งที่รองรับ:
- /favorite_add <ข้อความ>             บันทึกรายการโปรด
- /favorite_list                       แสดง N รายการล่าสุด (ค่าดีฟอลต์ 10)
- /favorite_remove <ลำดับ|ข้อความ>    ลบตามลำดับ (ตัวเลขเริ่มที่ 1) หรือระบุข้อความที่ต้องการลบ

จุดเด่นเวอร์ชันนี้:
- ใช้ parse_mode=HTML พร้อม escape ทุกจุด (กันฟอร์แมตพัง/สคริปต์ฝัง)
- แสดงกำลังพิมพ์ (typing action)
- แบ่งข้อความยาวอัตโนมัติ ≤ 4096 ตัวอักษร
- จำกัดความยาวที่ “เก็บ” ผ่าน ENV: FAVORITE_MAX_CHARS (ดีฟอลต์ 2000)
- จำกัดจำนวนรายการที่แสดงผ่าน ENV: FAVORITE_LIST_LIMIT (ดีฟอลต์ 10)
"""

from __future__ import annotations
import os
import re
import html
from typing import List, Dict

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from utils.favorite_utils import add_favorite, get_favorites, remove_favorite

# ===== Config via ENV =====
TELEGRAM_MESSAGE_LIMIT = 4096
FAVORITE_MAX_CHARS = int(os.getenv("FAVORITE_MAX_CHARS", "2000"))
FAVORITE_LIST_LIMIT = int(os.getenv("FAVORITE_LIST_LIMIT", "10"))

# ===== Small helpers =====
def _uid(update: Update) -> str:
    """คืน user_id เป็น string (เผื่อ storage ใช้ str เป็นคีย์)"""
    return str(update.effective_user.id) if update and update.effective_user else "unknown"

def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _normalize_text(s: str) -> str:
    """ลด zero-width, normalize แถว/ช่องว่าง และตัดความยาวตาม FAVORITE_MAX_CHARS"""
    if not s:
        return ""
    s = s.replace("\x00", "")
    s = re.sub(r"[\u200B-\u200D\uFEFF]", "", s)  # zero-width chars
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # บีบช่องว่างซ้ำภายในบรรทัด
    lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in s.split("\n")]
    # ลบแถวว่างติดกันให้เหลือไม่เกิน 1
    cleaned: List[str] = []
    for ln in lines:
        if ln == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(ln)
    out = "\n".join(cleaned).strip()
    return out[:FAVORITE_MAX_CHARS]

def _format_list(items: List[Dict], max_items: int) -> str:
    """จัดรูปแบบรายการโปรดให้ปลอดภัยต่อ HTML"""
    if not items:
        return "📭 คุณยังไม่มีรายการโปรดเลยครับ"
    lines: List[str] = [f"📌 <b>รายการโปรดของคุณ (ล่าสุด {max_items} รายการ)</b>"]
    for i, item in enumerate(items[:max_items], start=1):
        q = _html_escape(item.get("text") or item.get("q") or "")
        dt = _html_escape(item.get("date") or "")
        q = q if q else "-"
        if dt:
            lines.append(f"{i}. <b>{q}</b>\n   🗓️ {dt}")
        else:
            lines.append(f"{i}. <b>{q}</b>")
    lines.append("\nลบรายการ: <code>/favorite_remove &lt;ลำดับ&gt;</code> หรือ <code>/favorite_remove &lt;ข้อความ&gt;</code>")
    return "\n".join(lines)

def _usage() -> str:
    return (
        "<b>วิธีใช้รายการโปรด</b>\n"
        "• เพิ่ม: <code>/favorite_add &lt;ข้อความ&gt;</code>\n"
        f"• ดูรายการ: <code>/favorite_list</code>  (แสดง {FAVORITE_LIST_LIMIT} รายการล่าสุด)\n"
        "• ลบ: <code>/favorite_remove &lt;ลำดับ&gt;</code> หรือ <code>/favorite_remove &lt;ข้อความ&gt;</code>"
    )

def _normalize_args(context: ContextTypes.DEFAULT_TYPE) -> List[str]:
    """ตัดช่องว่างส่วนเกิน และกรอง arg ว่างออก (join เหลือสตริงเดียว)"""
    args = (context.args or [])
    return [a for a in (" ".join(args).strip(),) if a]

async def _send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int | str) -> None:
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    except Exception:
        pass

async def _reply_html(update: Update, text: str, context: ContextTypes.DEFAULT_TYPE, disable_preview: bool = True) -> None:
    """ส่งข้อความแบบ HTML โดยแบ่งเป็นชิ้น ≤ 4096 อัตโนมัติ"""
    if not text:
        return
    chunks: List[str] = []
    buf = ""
    for line in text.splitlines(True):  # เก็บ \n
        if len(buf) + len(line) <= TELEGRAM_MESSAGE_LIMIT:
            buf += line
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            # ถ้าบรรทัดยาวเกิน limit เอง ให้ตัดท่อน
            while len(line) > TELEGRAM_MESSAGE_LIMIT:
                chunks.append(line[:TELEGRAM_MESSAGE_LIMIT])
                line = line[TELEGRAM_MESSAGE_LIMIT:]
            buf = line
    if buf:
        chunks.append(buf)

    # ตัดต่อด้วยช่องว่างถ้าชิ้นไหนยังยาว (กรณีไม่มี \n)
    fixed: List[str] = []
    for c in chunks:
        if len(c) <= TELEGRAM_MESSAGE_LIMIT:
            fixed.append(c)
            continue
        wbuf = ""
        for w in c.split(" "):
            add = (w + " ")
            if len(wbuf) + len(add) > TELEGRAM_MESSAGE_LIMIT:
                fixed.append(wbuf.rstrip())
                wbuf = ""
            wbuf += add
        if wbuf:
            fixed.append(wbuf.rstrip())

    for piece in (fixed or [""]):
        await update.message.reply_text(
            piece,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=disable_preview
        )

# ===== Handlers =====
async def favorite_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_id = _uid(update)

    args = _normalize_args(context)
    if not args:
        await _reply_html(update, "❗️ โปรดพิมพ์ข้อความต่อท้ายคำสั่ง เช่น:\n<code>/favorite_add วิธีตั้งศูนย์ล้อ</code>", context)
        return

    text_raw = args[0]
    text_norm = _normalize_text(text_raw)
    if not text_norm.strip():
        await _reply_html(update, "❗️ กรุณาระบุข้อความที่ต้องการบันทึก", context)
        return

    await _send_typing(context, chat_id)
    try:
        ok = add_favorite(user_id, text_norm)
        if ok:
            preview = _html_escape(text_norm[:160] + ("…" if len(text_norm) > 160 else ""))
            await _reply_html(update, f"⭐️ บันทึกรายการโปรดเรียบร้อยแล้วครับ\nตัวอย่างที่บันทึก: <i>{preview}</i>", context)
        else:
            await _reply_html(update, "📌 ข้อความนี้มีอยู่ในรายการโปรดของคุณแล้ว", context)
    except Exception as e:
        emsg = _html_escape(str(e))
        await _reply_html(update, f"❌ บันทึกล้มเหลว: <code>{emsg}</code>", context)

async def favorite_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await _send_typing(context, chat_id)
    try:
        favs = get_favorites(_uid(update), limit=FAVORITE_LIST_LIMIT) or []
        body = _format_list(favs, max_items=FAVORITE_LIST_LIMIT)
        await _reply_html(update, body, context)
    except Exception as e:
        emsg = _html_escape(str(e))
        await _reply_html(update, f"❌ ดึงรายการโปรดไม่สำเร็จ: <code>{emsg}</code>", context)

async def favorite_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    args = _normalize_args(context)
    if not args:
        await _reply_html(
            update,
            "❗️ โปรดระบุสิ่งที่ต้องการลบ เช่น\n"
            "<code>/favorite_remove 2</code>   (ลบรายการลำดับที่ 2)\n"
            "<code>/favorite_remove วิธีตั้งศูนย์ล้อ</code>",
            context,
        )
        return

    target = args[0].strip()
    await _send_typing(context, chat_id)

    try:
        # ลบได้ 2 แบบ: ตาม 'ลำดับ' (ตัวเลขเริ่มที่ 1) หรือ 'ข้อความ'
        if target.isdigit():
            idx = int(target)
            if idx < 1:
                await _reply_html(update, "ลำดับต้องเริ่มที่ 1 ขึ้นไปครับ", context)
                return

            # เสริม: แจ้งช่วงลำดับที่เหมาะสม
            try:
                current = get_favorites(_uid(update), limit=FAVORITE_LIST_LIMIT) or []
                n = len(current)
                if n and idx > n:
                    await _reply_html(update, f"พบทั้งหมด {n} รายการ (ล่าสุด) — โปรดระบุ 1..{n}", context)
                    return
            except Exception:
                pass

            ok = remove_favorite(_uid(update), index=idx)  # ยูทิลควรรองรับ parameter index
        else:
            ok = remove_favorite(_uid(update), text=target)  # ยูทิลควรรองรับ parameter text

        if ok:
            await _reply_html(update, "🗑️ ลบรายการโปรดเรียบร้อยแล้วครับ", context)
        else:
            await _reply_html(update, "ไม่พบรายการตามที่ระบุครับ", context)
    except Exception as e:
        emsg = _html_escape(str(e))
        await _reply_html(update, f"❌ ลบรายการโปรดไม่สำเร็จ: <code>{emsg}</code>", context)

# (ออปชัน) เผื่อคุณอยากผูก /favorite_help
async def favorite_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply_html(update, _usage(), context)
