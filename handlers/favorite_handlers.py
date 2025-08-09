# handlers/favorite_handlers.py
# -*- coding: utf-8 -*-
"""
ฟังก์ชันจัดการ 'รายการโปรด' ด้วย python-telegram-bot (async)
คำสั่งที่รองรับ:
- /favorite_add <ข้อความ>        บันทึกรายการโปรด
- /favorite_list                  แสดง 10 รายการล่าสุด
- /favorite_remove <ลำดับ|ข้อความ> ลบตามลำดับ (ตัวเลข) หรือระบุข้อความที่ต้องการลบ
"""

from __future__ import annotations
import html
from typing import List, Dict

from telegram import Update
from telegram.ext import ContextTypes

from utils.favorite_utils import add_favorite, get_favorites, remove_favorite


def _uid(update: Update) -> str:
    """คืน user_id เป็น string (เผื่อยูทิลฝั่ง storage ใช้ str เป็นคีย์)"""
    return str(update.effective_user.id) if update and update.effective_user else "unknown"


def _normalize_args(context: ContextTypes.DEFAULT_TYPE) -> List[str]:
    """ตัดช่องว่างส่วนเกิน และกรอง arg ว่างออก"""
    args = (context.args or [])
    return [a for a in (" ".join(args).strip(),) if a]


def _format_list(items: List[Dict], max_items: int = 10) -> str:
    """จัดรูปแบบรายการโปรดให้ปลอดภัยต่อ HTML"""
    lines: List[str] = []
    for i, item in enumerate(items[:max_items], start=1):
        q = html.escape(item.get("text") or item.get("q") or "")
        dt = html.escape(item.get("date") or "")
        lines.append(f"{i}. <b>{q}</b>\n   🗓️ {dt}")
    return "\n".join(lines)


async def favorite_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _uid(update)

    args = _normalize_args(context)
    if not args:
        await update.message.reply_text(
            "❗️ โปรดพิมพ์ข้อความต่อท้ายคำสั่ง เช่น:\n"
            "/favorite_add วิธีตั้งศูนย์ล้อ"
        )
        return

    text = args[0]
    if not text.strip():
        await update.message.reply_text("❗️ กรุณาระบุข้อความที่ต้องการบันทึก")
        return

    try:
        ok = add_favorite(user_id, text)
        if ok:
            await update.message.reply_text("⭐️ บันทึกรายการโปรดเรียบร้อยแล้วครับ")
        else:
            await update.message.reply_text("📌 ข้อความนี้มีอยู่ในรายการโปรดของคุณแล้ว")
    except Exception as e:
        await update.message.reply_text(f"❌ บันทึกล้มเหลว: {e}")


async def favorite_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _uid(update)
    try:
        favs = get_favorites(user_id, limit=10) or []
        if not favs:
            await update.message.reply_text("📭 คุณยังไม่มีรายการโปรดเลยครับ")
            return

        body = _format_list(favs, max_items=10)
        await update.message.reply_text(
            f"📌 <b>รายการโปรดของคุณ (ล่าสุด 10 รายการ)</b>\n{body}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ดึงรายการโปรดไม่สำเร็จ: {e}")


async def favorite_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _uid(update)

    args = _normalize_args(context)
    if not args:
        await update.message.reply_text(
            "❗️ โปรดระบุสิ่งที่ต้องการลบ เช่น\n"
            "/favorite_remove 2   (ลบรายการลำดับที่ 2)\n"
            "/favorite_remove วิธีตั้งศูนย์ล้อ"
        )
        return

    target = args[0]

    try:
        # ลบได้ 2 แบบ: ตาม 'ลำดับ' (ตัวเลข) หรือ 'ข้อความ'
        if target.isdigit():
            idx = int(target)
            ok = remove_favorite(user_id, index=idx)  # ยูทิลควรรองรับ parameter index
        else:
            ok = remove_favorite(user_id, text=target)  # ยูทิลควรรองรับ parameter text

        if ok:
            await update.message.reply_text("🗑️ ลบรายการโปรดเรียบร้อยแล้วครับ")
        else:
            await update.message.reply_text("ไม่พบรายการตามที่ระบุครับ")
    except Exception as e:
        await update.message.reply_text(f"❌ ลบรายการโปรดไม่สำเร็จ: {e}")
