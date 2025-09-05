# handlers/lottery.py
# -*- coding: utf-8 -*-
"""
Handler for fetching the latest lottery results (Thai Government Lottery).
Stable version: message_utils (retry/auto-chunk/no-echo), HTML-safe formatting,
and robust handling for both string and dict payloads from utils.lottery_utils.
"""
from __future__ import annotations
from typing import Dict, Any, Iterable

from utils.message_utils import send_message, send_typing_action
from utils.lottery_utils import get_lottery_result


# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _looks_html(s: str) -> bool:
    if not s:
        return False
    return ("</" in s) or ("<b>" in s) or ("<i>" in s) or ("<code>" in s) or ("<br" in s)

def _fmt_numbers(val: Any) -> str:
    """รองรับค่าที่เป็น str / list / tuple → คืนเป็นสตริงสวย ๆ (HTML escaped)"""
    if val is None:
        return "-"
    if isinstance(val, (list, tuple, set)):
        return ", ".join(_html_escape(str(x)) for x in val)
    return _html_escape(str(val))

def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _format_dict_payload(d: Dict[str, Any]) -> str:
    """
    แปลง dict ผลสลากให้เป็นข้อความ HTML แบบยืดหยุ่น:
    รองรับคีย์ยอดนิยม เช่น:
      - draw_date/date/period
      - prize_first/first_prize
      - front3/three_front/first3
      - back3/three_back/last3
      - last2/two_back
    ถ้าไม่พบคีย์มาตรฐาน จะพิมพ์รายการ key:value ทั้งหมด
    """
    if not d:
        return "⚠️ ไม่พบข้อมูลผลสลาก"

    date_val = _first_present(d, ("draw_date", "date", "period", "issue", "updated", "updated_at", "time"))
    first     = _first_present(d, ("prize_first", "first_prize", "รางวัลที่1", "prize_1"))
    front3    = _first_present(d, ("front3", "three_front", "front_3", "เลขหน้า3ตัว"))
    back3     = _first_present(d, ("back3", "three_back", "back_3", "เลขท้าย3ตัว"))
    last2     = _first_present(d, ("last2", "two_back", "back_2", "เลขท้าย2ตัว"))

    lines = ["🎫 <b>ผลสลากกินแบ่งรัฐบาล งวดล่าสุด</b>"]
    if date_val:
        lines.append(f"🗓️ งวดวันที่: <code>{_html_escape(str(date_val))}</code>")

    had_any = False
    if first is not None:
        lines.append(f"• รางวัลที่ 1: <b>{_fmt_numbers(first)}</b>")
        had_any = True
    if front3 is not None:
        lines.append(f"• เลขหน้า 3 ตัว: <b>{_fmt_numbers(front3)}</b>")
        had_any = True
    if back3 is not None:
        lines.append(f"• เลขท้าย 3 ตัว: <b>{_fmt_numbers(back3)}</b>")
        had_any = True
    if last2 is not None:
        lines.append(f"• เลขท้าย 2 ตัว: <b>{_fmt_numbers(last2)}</b>")
        had_any = True

    if had_any:
        return "\n".join(lines)

    # Fallback: dump ทุก key:value ที่มี (กรณีรูปแบบไม่ตรงคาด)
    lines.append("")
    for k, v in d.items():
        lines.append(f"• <code>{_html_escape(str(k))}</code>: {_fmt_numbers(v)}")
    return "\n".join(lines)


# ===== Main Handler =====
def handle_lottery(user_info: Dict[str, Any], user_text: str) -> None:
    """
    ตัวหลักสำหรับ main_handler:
    - แสดงกำลังพิมพ์
    - เรียก get_lottery_result() (ดึง 'งวดล่าสุด' เสมอ)
    - ส่งผลลัพธ์แบบ HTML ปลอดภัย
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        # แจ้งสถานะกำลังทำงาน
        send_typing_action(chat_id, "typing")
        send_message(chat_id, "🔎 กำลังตรวจสอบผลสลากกินแบ่งรัฐบาลงวดล่าสุดสักครู่ครับ…")

        data = get_lottery_result()

        # โครงสร้างแบบ dict → ฟอร์แมตสวย ๆ
        if isinstance(data, dict):
            msg = _format_dict_payload(data)
            send_message(chat_id, msg, parse_mode="HTML")
            return

        # โครงสร้างแบบ str → ถ้าเป็น HTML แล้วส่งตรง, ไม่งั้น escape และห่อหัวเรื่อง
        if isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลผลสลากในขณะนี้", parse_mode="HTML")
                return
            if _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"🎫 <b>ผลสลากกินแบ่งรัฐบาล งวดล่าสุด</b>\n\n{_html_escape(s)}", parse_mode="HTML")
            return

        # ไม่เข้าเคสที่รู้จัก
        send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลผลสลากในขณะนี้", parse_mode="HTML")

    except Exception as e:
        print(f"[handle_lottery] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการดึงผลสลากครับ", parse_mode="HTML")


# (ออปชัน) รองรับโค้ดเก่าที่อาจเรียกด้วย chat_id ตรง ๆ
def handle_lottery_legacy(chat_id: int | str, user_text: str) -> None:
    try:
        send_typing_action(chat_id, "typing")
        send_message(chat_id, "🔎 กำลังตรวจสอบผลสลากกินแบ่งรัฐบาลงวดล่าสุดสักครู่ครับ…")
        data = get_lottery_result()
        if isinstance(data, dict):
            send_message(chat_id, _format_dict_payload(data), parse_mode="HTML")
        elif isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลผลสลากในขณะนี้", parse_mode="HTML")
            elif _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"🎫 <b>ผลสลากกินแบ่งรัฐบาล งวดล่าสุด</b>\n\n{_html_escape(s)}", parse_mode="HTML")
        else:
            send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลผลสลากในขณะนี้", parse_mode="HTML")
    except Exception as e:
        print(f"[handle_lottery_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงผลสลากครับ", parse_mode="HTML")
