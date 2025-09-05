# handlers/faq.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List
import os

from utils.message_utils import send_message, send_typing_action
from utils.memory_store import add_or_update_faq, get_faq_answer, get_all_faqs

# ===== Admin guard (secure-by-default) =====
_ADMIN_IDS = set()
try:
    sa = (os.getenv("SUPER_ADMIN_ID") or "").strip()
    if sa:
        _ADMIN_IDS.add(int(sa))
    admin_ids = (os.getenv("ADMIN_IDS") or "").strip()
    if admin_ids:
        for x in admin_ids.split(","):
            x = x.strip()
            if x:
                _ADMIN_IDS.add(int(x))
except Exception:
    # ไม่ให้ process ตายเพราะ ENV เพี้ยน
    pass

def _is_admin(user_id: int | str) -> bool:
    try:
        uid = int(str(user_id))
    except Exception:
        return False
    # ถ้ายังไม่ตั้ง ADMIN ใครก็ไม่ใช่แอดมิน (secure-by-default)
    return uid in _ADMIN_IDS

# ===== Small helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _usage_add() -> str:
    return (
        "วิธีใช้การเพิ่ม/แก้ไข FAQ:\n"
        "<code>/add_faq &lt;คำถามหรือคีย์เวิร์ด&gt; &lt;คำตอบ&gt;</code>\n"
        "เช่น: <code>/add_faq เปิดใช้งานยังไง</code> <i>พิมพ์ /start แล้วทำตามขั้นตอน…</i>"
    )

def _usage_query() -> str:
    return (
        "วิธีใช้:\n"
        "• ดูรายการทั้งหมด: <code>/faq</code>\n"
        "• ค้นหาคำตอบ: <code>/faq &lt;keyword&gt;</code>\n"
        "• เพิ่ม/แก้ไข (แอดมิน): <code>/add_faq &lt;keyword&gt; &lt;answer&gt;</code>"
    )

# ===== Main handler =====
def handle_faq(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    user_id = user_info["profile"]["user_id"]
    text = (user_text or "").strip()
    parts = text.split(maxsplit=2)
    command = (parts[0].lower() if parts else "")

    # ---- /add_faq <keyword> <answer>  (admin only) ----
    if command == "/add_faq":
        if not _is_admin(user_id):
            send_message(chat_id, "คำสั่งนี้สำหรับแอดมินเท่านั้นครับ (โปรดตั้ง SUPER_ADMIN_ID/ADMIN_IDS)", parse_mode="HTML")
            return
        if len(parts) < 3:
            send_message(chat_id, _usage_add(), parse_mode="HTML")
            return

        keyword_raw = parts[1].strip()
        answer_raw  = parts[2].strip()
        if not keyword_raw or not answer_raw:
            send_message(chat_id, _usage_add(), parse_mode="HTML")
            return

        # บันทึก (add_or_update)
        ok = False
        try:
            ok = add_or_update_faq(keyword_raw, answer_raw, user_id)
        except Exception as e:
            print(f"[handle_faq] add_or_update error: {e}")
            ok = False

        if ok:
            send_message(
                chat_id,
                f"✅ บันทึก FAQ สำหรับคำว่า <code>{_html_escape(keyword_raw)}</code> เรียบร้อยแล้วครับ",
                parse_mode="HTML",
            )
        else:
            send_message(chat_id, "❌ เกิดข้อผิดพลาดในการบันทึก FAQ", parse_mode="HTML")
        return

    # ---- /faq … (list or get) ----
    # /faq (list all)
    if command == "/faq" and len(parts) == 1:
        send_typing_action(chat_id, "typing")
        try:
            faqs = get_all_faqs() or []
        except Exception as e:
            print(f"[handle_faq] get_all_faqs error: {e}")
            faqs = []

        if not faqs:
            send_message(chat_id, "ยังไม่มี FAQ ในระบบครับ — ใช้ <code>/add_faq</code> เพื่อเพิ่มได้ (แอดมิน)", parse_mode="HTML")
            return

        # สร้างลิสต์คีย์เวิร์ดสวย ๆ (escape ทุกตัว)
        lines: List[str] = [ "<b>รายการ FAQ ทั้งหมด</b>" ]
        for item in faqs:
            try:
                kw = item.get("keyword") if isinstance(item, dict) else str(item)
            except Exception:
                kw = str(item)
            kw = _html_escape(kw or "-")
            lines.append(f"• <code>{kw}</code>")
        lines.append("")  # เว้นบรรทัด
        lines.append(_usage_query())

        send_message(chat_id, "\n".join(lines), parse_mode="HTML")
        return

    # /faq <keyword>  (answer)
    if command == "/faq" and len(parts) >= 2:
        keyword_raw = parts[1].strip()
        if not keyword_raw:
            send_message(chat_id, _usage_query(), parse_mode="HTML")
            return

        send_typing_action(chat_id, "typing")
        try:
            answer = get_faq_answer(keyword_raw)
        except Exception as e:
            print(f"[handle_faq] get_faq_answer error: {e}")
            answer = None

        if answer:
            send_message(
                chat_id,
                f"💡 <b>คำตอบสำหรับ</b> <code>{_html_escape(keyword_raw)}</code>\n\n{_html_escape(str(answer))}",
                parse_mode="HTML",
            )
        else:
            send_message(
                chat_id,
                f"❓ ไม่พบคำตอบสำหรับ <code>{_html_escape(keyword_raw)}</code> ครับ\n\n{_usage_query()}",
                parse_mode="HTML",
            )
        return

    # fallback (ไม่ตรงรูปแบบ)
    send_message(chat_id, _usage_query(), parse_mode="HTML")
