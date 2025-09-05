# handlers/stock.py
# -*- coding: utf-8 -*-
"""
Handler for fetching and displaying stock information using Finance Utils.
Stable + safe:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo + typing action)
- parse_mode=HTML พร้อม escape ทุกข้อความภายนอก
- รองรับหลายสัญลักษณ์ต่อครั้ง (เว้นวรรค/คั่นด้วยจุลภาค)
- เติม .BK ให้อัตโนมัติเมื่อเหมาะสม (ตั้งค่าได้ผ่าน ENV)
"""

from __future__ import annotations
from typing import Dict, Any, Iterable, List
import os
import re

from utils.message_utils import send_message, send_typing_action
from utils.finance_utils import get_stock_info_from_google


# ===== Config via ENV =====
# เปิด/ปิด heuristic “ถ้าไม่มี suffix ให้ถือว่าเป็นหุ้นไทยแล้วเติม .BK”
_STOCK_ASSUME_TH_IF_NO_SUFFIX = os.getenv("STOCK_ASSUME_TH_IF_NO_SUFFIX", "1") == "1"
# จำกัดจำนวนสัญลักษณ์ต่อคำสั่ง
_STOCK_MAX_SYMBOLS = int(os.getenv("STOCK_MAX_SYMBOLS", "5"))

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
    parts: List[str] = []
    if chg not in (None, ""):
        try:
            v = float(str(chg).replace(",", ""))
            sign = "+" if v > 0 else ""
        except Exception:
            sign = "" if str(chg).strip().startswith("-") else "+"
        parts.append(f"{sign}{_html_escape(str(chg))}")
    if pct not in (None, ""):
        s = str(pct).strip()
        if not s.endswith("%"):
            try:
                v = float(s.replace(",", ""))
                s = f"{v:+.2f}%"
            except Exception:
                if not (s.startswith("+") or s.startswith("-")):
                    s = f"+{s}"
        parts.append(s)
    return " / ".join(parts) if parts else "—"

def _fmt_kv(label: str, val: Any) -> str:
    return f"• {label}: <b>{_html_escape(str(val))}</b>"

def _fmt_stock_dict(d: Dict[str, Any], norm_symbol: str) -> str:
    """
    รองรับคีย์แพร่หลาย:
    - name/company, symbol/ticker, exchange/market, currency
    - price/last, change, percent
    - open, high, low, prev_close/previous_close
    - volume, market_cap/mcap
    - updated/updated_at/time/as_of
    """
    name   = _first_present(d, ("name", "company", "company_name", "longName"))
    symbol = _first_present(d, ("symbol", "ticker")) or norm_symbol
    exch   = _first_present(d, ("exchange", "market"))
    curr   = _first_present(d, ("currency", "curr", "unit"))

    price  = _first_present(d, ("price", "last", "regularMarketPrice", "value"))
    chg    = _first_present(d, ("change", "chg", "regularMarketChange"))
    pct    = _first_present(d, ("percent", "change_percent", "regularMarketChangePercent"))
    open_  = d.get("open")
    high   = d.get("high")
    low    = d.get("low")
    prev   = _first_present(d, ("prev_close", "previous_close", "prevClose"))
    vol    = _first_present(d, ("volume", "vol"))
    mcap   = _first_present(d, ("market_cap", "mcap", "marketCap"))
    upd    = _first_present(d, ("updated", "updated_at", "time", "as_of"))

    title = f"📈 <b>{_html_escape(name) if name else _html_escape(symbol)}</b>"
    subtitle_bits: List[str] = []
    if symbol:
        subtitle_bits.append(f"<code>{_html_escape(str(symbol))}</code>")
    if exch:
        subtitle_bits.append(_html_escape(str(exch)))
    header = title + (" — " + " · ".join(subtitle_bits) if subtitle_bits else "")

    lines: List[str] = [header]

    if price is not None:
        arr = _arrow(chg)
        price_str = _fmt_price(price)
        chg_str = _fmt_change(chg, pct)
        unit = f" {_html_escape(str(curr))}" if curr else ""
        lines.append(f"• ราคา: <b>{price_str}</b>{unit}  ({arr} {chg_str})")

    ohlc = []
    if open_ is not None: ohlc.append(f"เปิด {_html_escape(str(open_))}")
    if high  is not None: ohlc.append(f"สูง {_html_escape(str(high))}")
    if low   is not None: ohlc.append(f"ต่ำ {_html_escape(str(low))}")
    if prev  is not None: ohlc.append(f"ปิดก่อนหน้า {_html_escape(str(prev))}")
    if ohlc:
        lines.append("• " + " / ".join(ohlc))

    extras = []
    if vol  is not None: extras.append(f"ปริมาณ { _html_escape(str(vol)) }")
    if mcap is not None: extras.append(f"มูลค่าตลาด { _html_escape(str(mcap)) }")
    if extras:
        lines.append("• " + " / ".join(extras))

    if upd:
        lines.append(f"🕒 อัปเดตล่าสุด: <code>{_html_escape(str(upd))}</code>")

    return "\n".join(lines)

def _normalize_symbol_token(raw: str, hint_text: str) -> str:
    """
    นโยบายเติม .BK:
    - ถ้าสตริงมี '.' หรือ ':' อยู่แล้ว → ไม่แตะ
    - ถ้าเป็นตัวอักษรล้วน ยาว 1–5 ตัว → เติม .BK เมื่อ _STOCK_ASSUME_TH_IF_NO_SUFFIX เปิดอยู่
      (ครอบคลุม AOT, PTT, KBANK, SCB, PTTEP ฯลฯ)
    - มิฉะนั้น → คืนค่าเดิม
    """
    s = (raw or "").strip().upper().replace("，", ",")
    if not s:
        return s
    if "." in s or ":" in s:
        return s
    if not s.isalnum():
        return s
    # มีตัวเลขปน เช่น BBL28, OR01 → ไม่เติม .BK โดยอัตโนมัติ
    if any(ch.isdigit() for ch in s):
        return s
    if 1 <= len(s) <= 5 and _STOCK_ASSUME_TH_IF_NO_SUFFIX:
        return f"{s}.BK"
    return s

def _extract_symbols(user_text: str) -> List[str]:
    """
    รับข้อความคำสั่ง แล้วแตกเป็นรายการสัญลักษณ์ (เว้นวรรค/คอมมา)
    ตัวอย่าง:
      '/stock AAPL' → ['AAPL']
      '/stock AOT PTT KBANK' → ['AOT', 'PTT', 'KBANK']
      '/stock AOT,PTT' → ['AOT', 'PTT']
    """
    t = (user_text or "").strip()
    if not t:
        return []
    # ตัด prefix /stock (ถ้ามี)
    if t.lower().startswith("/stock"):
        t = t[len("/stock"):].strip()
    # แยกด้วย comma หรือเว้นวรรค
    t = t.replace(",", " ").replace("，", " ")
    syms = [s for s in t.split() if s]
    return syms[:_STOCK_MAX_SYMBOLS]

# ===== Main Handler =====
def handle_stock(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Parses the stock symbol(s), fetches via Finance Utils, and sends nicely formatted results.
    รองรับหลายสัญลักษณ์ (สูงสุด _STOCK_MAX_SYMBOLS)
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        symbols = _extract_symbols(user_text)
        if not symbols:
            send_message(
                chat_id,
                "วิธีใช้: <code>/stock &lt;สัญลักษณ์&gt;</code> (รองรับหลายตัว, คั่นด้วยเว้นวรรคหรือจุลภาค)\n"
                "เช่น <code>/stock AOT PTT KBANK</code> หรือ <code>/stock AAPL</code>",
                parse_mode="HTML",
            )
            return

        # เตรียมสัญลักษณ์ที่ normalize แล้ว (เติม .BK เมื่อเหมาะสม)
        norm_symbols: List[str] = [_normalize_symbol_token(s, user_text) for s in symbols]

        # แจ้งกำลังค้นหา
        send_typing_action(chat_id, "typing")
        if len(norm_symbols) == 1:
            send_message(chat_id, f"🔎 กำลังค้นหาข้อมูลหุ้น <code>{_html_escape(norm_symbols[0])}</code> จาก Google Finance ครับ…", parse_mode="HTML")
        else:
            joined = ", ".join(f"<code>{_html_escape(x)}</code>" for x in norm_symbols)
            send_message(chat_id, f"🔎 กำลังค้นหาข้อมูลหุ้น {joined} จาก Google Finance ครับ…", parse_mode="HTML")

        # ดึงข้อมูลทีละตัวและส่งผลลัพธ์
        for sym in norm_symbols:
            try:
                data = get_stock_info_from_google(sym)
            except Exception as e:
                print(f"[handle_stock] get_stock_info_from_google error for {sym}: {e}")
                send_message(chat_id, f"❌ ดึงข้อมูล <code>{_html_escape(sym)}</code> ไม่สำเร็จ", parse_mode="HTML")
                continue

            # dict → ฟอร์แมตละเอียด
            if isinstance(data, dict):
                msg = _fmt_stock_dict(data, norm_symbol=sym)
                send_message(chat_id, msg, parse_mode="HTML")
                continue

            # str → ถ้าเป็น HTML ส่งตรง; ไม่งั้นห่อหัวเรื่อง
            if isinstance(data, str):
                s = data.strip()
                if not s:
                    send_message(chat_id, f"ขออภัยครับ ไม่พบข้อมูลสำหรับ <code>{_html_escape(sym)}</code>", parse_mode="HTML")
                    continue
                if _looks_html(s):
                    send_message(chat_id, s, parse_mode="HTML")
                else:
                    send_message(
                        chat_id,
                        f"📈 <b>ข้อมูลหุ้น</b> — <code>{_html_escape(sym)}</code>\n\n{_html_escape(s)}",
                        parse_mode="HTML",
                    )
                continue

            # ไม่เข้าเคสที่รู้จัก
            send_message(chat_id, f"ขออภัยครับ ไม่พบข้อมูลสำหรับ <code>{_html_escape(sym)}</code>", parse_mode="HTML")

    except Exception as e:
        print(f"[handle_stock] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการประมวลผลคำขอของคุณครับ", parse_mode="HTML")


# (ออปชัน) Legacy signature: รับ chat_id ตรง ๆ
def handle_stock_legacy(chat_id: int | str, user_text: str) -> None:
    try:
        symbols = _extract_symbols(user_text)
        if not symbols:
            send_message(chat_id, "วิธีใช้: <code>/stock &lt;สัญลักษณ์&gt;</code>", parse_mode="HTML")
            return

        norm_symbols = [_normalize_symbol_token(s, user_text) for s in symbols]

        send_typing_action(chat_id, "typing")
        if len(norm_symbols) == 1:
            send_message(chat_id, f"🔎 กำลังค้นหาข้อมูลหุ้น <code>{_html_escape(norm_symbols[0])}</code> จาก Google Finance ครับ…", parse_mode="HTML")
        else:
            joined = ", ".join(f"<code>{_html_escape(x)}</code>" for x in norm_symbols)
            send_message(chat_id, f"🔎 กำลังค้นหาข้อมูลหุ้น {joined} จาก Google Finance ครับ…", parse_mode="HTML")

        for sym in norm_symbols:
            try:
                data = get_stock_info_from_google(sym)
            except Exception as e:
                print(f"[handle_stock_legacy] get_stock_info_from_google error for {sym}: {e}")
                send_message(chat_id, f"❌ ดึงข้อมูล <code>{_html_escape(sym)}</code> ไม่สำเร็จ", parse_mode="HTML")
                continue

            if isinstance(data, dict):
                send_message(chat_id, _fmt_stock_dict(data, norm_symbol=sym), parse_mode="HTML")
            elif isinstance(data, str):
                s = data.strip()
                if not s:
                    send_message(chat_id, f"ขออภัยครับ ไม่พบข้อมูลสำหรับ <code>{_html_escape(sym)}</code>", parse_mode="HTML")
                elif _looks_html(s):
                    send_message(chat_id, s, parse_mode="HTML")
                else:
                    send_message(chat_id, f"📈 <b>ข้อมูลหุ้น</b> — <code>{_html_escape(sym)}</code>\n\n{_html_escape(s)}", parse_mode="HTML")
            else:
                send_message(chat_id, f"ขออภัยครับ ไม่พบข้อมูลสำหรับ <code>{_html_escape(sym)}</code>", parse_mode="HTML")
    except Exception as e:
        print(f"[handle_stock_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำขอของคุณครับ", parse_mode="HTML")
