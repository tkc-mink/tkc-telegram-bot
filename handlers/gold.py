# handlers/gold.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

from utils.message_utils import send_message, send_typing_action
from utils.gold_utils import get_gold_price

def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _looks_html(s: str) -> bool:
    if not s:
        return False
    # คร่าว ๆ: มีแท็กเปิด-ปิดอย่างน้อยหนึ่งอัน
    return ("</" in s) or ("<b>" in s) or ("<i>" in s) or ("<code>" in s) or ("<br" in s)

def _format_dict_payload(d: Dict[str, Any]) -> str:
    """
    แปลง dict ราคาทองเป็นข้อความ HTML อย่างยืดหยุ่น
    รองรับ key ที่พบบ่อย เช่น 'bar_buy', 'bar_sell', 'ornament_buy', 'ornament_sell', 'updated'
    ถ้า key ไม่ตรง ก็พิมพ์รายการคู่ key:value ให้ทั้งหมด
    """
    if not d:
        return "⚠️ ไม่พบข้อมูลราคาทอง"

    # กรณีมีคีย์มาตรฐาน
    bar_buy  = d.get("bar_buy") or d.get("bar_buy_price")
    bar_sell = d.get("bar_sell") or d.get("bar_sell_price")
    or_buy   = d.get("ornament_buy") or d.get("ornament_buy_price")
    or_sell  = d.get("ornament_sell") or d.get("ornament_sell_price")
    updated  = d.get("updated") or d.get("updated_at") or d.get("time")

    lines = ["📊 <b>ราคาทองวันนี้</b>"]
    had_any = False
    if bar_buy or bar_sell:
        lines.append(f"• ทองแท่ง: ซื้อ <b>{_html_escape(str(bar_buy or '-'))}</b> / ขาย <b>{_html_escape(str(bar_sell or '-'))}</b>")
        had_any = True
    if or_buy or or_sell:
        lines.append(f"• ทองรูปพรรณ: ซื้อ <b>{_html_escape(str(or_buy or '-'))}</b> / ขาย <b>{_html_escape(str(or_sell or '-'))}</b>")
        had_any = True
    if updated:
        lines.append(f"🕒 อัปเดตล่าสุด: <code>{_html_escape(str(updated))}</code>")

    if had_any:
        return "\n".join(lines)

    # ถ้าไม่เข้าเคสมาตรฐาน ให้ dump ทุกคู่ key:value ที่มี
    lines.append("")
    for k, v in d.items():
        lines.append(f"• <code>{_html_escape(str(k))}</code>: {_html_escape(str(v))}")
    return "\n".join(lines)

def handle_gold(user_info: Dict[str, Any], user_text: str) -> None:
    """
    เวอร์ชันมาตรฐาน (ใช้กับ main_handler): รับ user_info, user_text
    - แสดงกำลังพิมพ์
    - เรียก get_gold_price()
    - ส่งผลลัพธ์แบบ HTML อย่างปลอดภัย
    """
    chat_id = user_info["profile"]["user_id"]

    try:
        send_typing_action(chat_id, "typing")

        data = get_gold_price()

        if isinstance(data, dict):
            msg = _format_dict_payload(data)
            send_message(chat_id, msg, parse_mode="HTML")
            return

        # กรณีเป็นข้อความ
        if isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาทองในขณะนี้")
                return

            # ถ้าดูเหมือนเป็น HTML อยู่แล้ว ส่งตรง; ไม่งั้น escape
            if _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"📊 <b>ราคาทองวันนี้</b>\n{_html_escape(s)}", parse_mode="HTML")
            return

        # ไม่เข้าเงื่อนไขที่รู้จัก
        send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาทองในขณะนี้")
    except Exception as e:
        print(f"[handle_gold] ERROR: {e}")
        send_message(chat_id, "❌ เกิดข้อผิดพลาดในการดึงข้อมูลราคาทองครับ")

# (ออปชัน) รองรับโค้ดเก่าที่เคยเรียกด้วย chat_id ตรง ๆ
def handle_gold_legacy(chat_id: int | str, user_text: str) -> None:
    try:
        send_typing_action(chat_id, "typing")
        data = get_gold_price()
        if isinstance(data, dict):
            send_message(chat_id, _format_dict_payload(data), parse_mode="HTML")
        elif isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาทองในขณะนี้")
            elif _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"📊 <b>ราคาทองวันนี้</b>\n{_html_escape(s)}", parse_mode="HTML")
        else:
            send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาทองในขณะนี้")
    except Exception as e:
        print(f"[handle_gold_legacy] ERROR: {e}")
        send_message(chat_id, "❌ เกิดข้อผิดพลาดในการดึงข้อมูลราคาทองครับ")
