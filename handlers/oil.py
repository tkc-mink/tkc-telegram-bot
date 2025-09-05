# handlers/oil.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Iterable

from utils.message_utils import send_message, send_typing_action
from utils.finance_utils import get_oil_price_from_google


# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _looks_html(s: str) -> bool:
    if not s:
        return False
    return ("</" in s) or ("<b>" in s) or ("<i>" in s) or ("<code>" in s) or ("<a " in s) or ("<br" in s)

def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _arrow(change: Any) -> str:
    try:
        v = float(str(change).replace(",", ""))
        if v > 0:
            return "📈"
        if v < 0:
            return "📉"
        return "➖"
    except Exception:
        return ""

def _fmt_price(x: Any) -> str:
    try:
        return f"{float(str(x).replace(',', '')):,.2f}"
    except Exception:
        return _html_escape(str(x))

def _fmt_change(chg: Any, pct: Any) -> str:
    out = []
    if chg not in (None, ""):
        sign = "+" if str(chg).strip().startswith("-") is False else ""
        # ถ้าเป็น 0 ไม่ต้องใส่ +
        try:
            v = float(str(chg).replace(",", ""))
            sign = "+" if v > 0 else ""  # 0 หรือ ลบ จะไม่ใส่ +
        except Exception:
            pass
        out.append(f"{sign}{_html_escape(str(chg))}")
    if pct not in (None, ""):
        s = str(pct)
        if not s.endswith("%"):
            # พยายามฟอร์แมตเป็นเปอร์เซ็นต์
            try:
                v = float(s.replace(",", ""))
                s = f"{v:+.2f}%"
            except Exception:
                pass
        out.append(s if s.startswith("+") or s.startswith("-") else f"+{s}")
    return " / ".join(out) if out else "—"

def _fmt_instrument(name: str, block: Dict[str, Any]) -> str:
    price   = _first_present(block, ("price", "last", "value"))
    change  = _first_present(block, ("change", "chg", "delta"))
    percent = _first_present(block, ("percent", "pct", "change_percent"))
    unit    = _first_present(block, ("currency", "unit"))
    arr     = _arrow(change)

    p = _fmt_price(price) if price is not None else "-"
    ch = _fmt_change(change, percent)

    # ตัวอย่าง: • WTI: 79.12 USD  (📈 +0.35 / +0.44%)
    unit_str = f" {_html_escape(str(unit))}" if unit else ""
    return f"• {name}: <b>{p}</b>{unit_str}  ({arr} {ch})"

def _format_dict_payload(d: Dict[str, Any]) -> str:
    """
    รองรับโครงสร้าง dict ยืดหยุ่น เช่น:
    {
      "WTI": {"price": 78.12, "change": 0.35, "percent": 0.45, "currency":"USD"},
      "Brent": {"price": 82.90, "change": -0.12, "percent": -0.14, "currency":"USD"},
      "updated": "2025-09-05 15:00 ICT"
    }
    หรือคีย์อื่นใกล้เคียง
    """
    if not d:
        return "⚠️ ไม่พบข้อมูลราคาน้ำมันในขณะนี้"

    wti   = _first_present(d, ("WTI", "wti", "WTI_crude", "wti_crude"))
    brent = _first_present(d, ("Brent", "brent", "Brent_crude", "brent_crude"))
    upd   = _first_present(d, ("updated", "updated_at", "time", "as_of"))

    lines = ["🛢️ <b>ราคาน้ำมันดิบวันนี้</b>"]
    had_any = False

    if isinstance(wti, dict):
        lines.append(_fmt_instrument("WTI", wti))
        had_any = True
    if isinstance(brent, dict):
        lines.append(_fmt_instrument("Brent", brent))
        had_any = True

    # กรณี util ส่งเป็น flat dict: {"wti_price":..., "brent_price":...}
    if not had_any:
        wti_price   = _first_present(d, ("wti_price", "WTI_price"))
        wti_change  = _first_present(d, ("wti_change", "WTI_change"))
        wti_percent = _first_present(d, ("wti_percent", "WTI_percent"))
        br_price    = _first_present(d, ("brent_price", "Brent_price"))
        br_change   = _first_present(d, ("brent_change", "Brent_change"))
        br_percent  = _first_present(d, ("brent_percent", "Brent_percent"))

        if any(x is not None for x in (wti_price, br_price)):
            if wti_price is not None:
                lines.append(_fmt_instrument("WTI", {"price": wti_price, "change": wti_change, "percent": wti_percent, "currency": "USD"}))
            if br_price is not None:
                lines.append(_fmt_instrument("Brent", {"price": br_price, "change": br_change, "percent": br_percent, "currency": "USD"}))
            had_any = True

    if upd:
        lines.append(f"🕒 อัปเดตล่าสุด: <code>{_html_escape(str(upd))}</code>")

    if had_any:
        return "\n".join(lines)

    # Fallback: dump ทุกคีย์
    lines.append("")
    for k, v in d.items():
        lines.append(f"• <code>{_html_escape(str(k))}</code>: {_html_escape(str(v))}")
    return "\n".join(lines)


# ===== Main Handler =====
def handle_oil(user_info: Dict[str, Any], user_text: str) -> None:
    """
    เวอร์ชันมาตรฐาน (ใช้กับ main_handler):
    - แสดงกำลังพิมพ์
    - เรียก get_oil_price_from_google()
    - ส่งผลลัพธ์แบบ HTML อย่างปลอดภัย
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        send_typing_action(chat_id, "typing")
        send_message(chat_id, "🔎 กำลังค้นหาราคาน้ำมันดิบ WTI และ Brent ครับ…", parse_mode="HTML")

        data = get_oil_price_from_google()

        if isinstance(data, dict):
            msg = _format_dict_payload(data)
            send_message(chat_id, msg, parse_mode="HTML")
            return

        if isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาน้ำมันในขณะนี้", parse_mode="HTML")
                return
            if _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"🛢️ <b>ราคาน้ำมันดิบวันนี้</b>\n\n{_html_escape(s)}", parse_mode="HTML")
            return

        send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาน้ำมันในขณะนี้", parse_mode="HTML")

    except Exception as e:
        print(f"[handle_oil] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการดึงข้อมูลราคาน้ำมันครับ", parse_mode="HTML")


# (ออปชัน) รองรับโค้ดเก่าที่เคยเรียกด้วย chat_id ตรง ๆ
def handle_oil_legacy(chat_id: int | str, user_text: str) -> None:
    try:
        send_typing_action(chat_id, "typing")
        send_message(chat_id, "🔎 กำลังค้นหาราคาน้ำมันดิบ WTI และ Brent ครับ…", parse_mode="HTML")
        data = get_oil_price_from_google()
        if isinstance(data, dict):
            send_message(chat_id, _format_dict_payload(data), parse_mode="HTML")
        elif isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาน้ำมันในขณะนี้", parse_mode="HTML")
            elif _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(chat_id, f"🛢️ <b>ราคาน้ำมันดิบวันนี้</b>\n\n{_html_escape(s)}", parse_mode="HTML")
        else:
            send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาน้ำมันในขณะนี้", parse_mode="HTML")
    except Exception as e:
        print(f"[handle_oil_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลราคาน้ำมันครับ", parse_mode="HTML")
