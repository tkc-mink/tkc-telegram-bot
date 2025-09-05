# handlers/crypto.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List
import re

from utils.finance_utils import get_crypto_price_from_google
from utils.message_utils import send_message, send_typing_action

# เหรียญยอดฮิต (ชื่อ → สัญลักษณ์) เพิ่มได้ตามต้องการ
_NAME_TO_SYMBOL = {
    # ไทย
    "บิตคอยน์": "BTC",
    "บิทคอยน์": "BTC",
    "อีเธอเรียม": "ETH",
    "เทเธอร์": "USDT",
    "บีเอ็นบี": "BNB",
    "บิเอนบี": "BNB",
    "โซลานา": "SOL",
    "โดชคอยน์": "DOGE",
    "ริปเปิล": "XRP",
    "ริพเพิล": "XRP",
    "คาร์ดาโน": "ADA",
    # อังกฤษ (ชื่อเต็มยอดนิยม)
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "tether": "USDT",
    "binance": "BNB",
    "solana": "SOL",
    "dogecoin": "DOGE",
    "ripple": "XRP",
    "cardano": "ADA",
}

_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,15}$")
_MAX_SYMBOLS = 8  # กัน spam/ยาวเกิน

def _extract_symbols(user_text: str) -> List[str]:
    """
    ดึงสัญลักษณ์เหรียญจากข้อความคำสั่ง:
    - รองรับหลายเหรียญ เว้นวรรคคั่น
    - รองรับรูปแบบ $btc, btc, BTC
    - แปลงชื่อไทย/อังกฤษยอดฮิตเป็นสัญลักษณ์
    - กรองซ้ำ, จำกัดจำนวน
    """
    if not user_text:
        return []

    parts = user_text.strip().split()
    # ตัดคำสั่งนำหน้า (/crypto)
    if parts and parts[0].lower().startswith("/crypto"):
        parts = parts[1:]

    out: List[str] = []
    seen = set()

    for raw in parts:
        if not raw:
            continue
        t = raw.strip().strip(",;|/").lstrip("$")  # ลอกสัญลักษณ์คั่นยอดนิยม
        if not t:
            continue

        # map ชื่อยอดฮิต → symbol
        key = t.lower()
        if key in _NAME_TO_SYMBOL:
            sym = _NAME_TO_SYMBOL[key]
        else:
            sym = t.upper()

        # กรองคำเชิงบรรยายที่ชอบพิมพ์ติดมาด้วย เช่น "price", "ราคา"
        if sym.lower() in ("price", "ราคา", "coin", "เหรียญ"):
            continue

        # ตรวจรูปแบบสัญลักษณ์
        if not _SYMBOL_RE.match(sym):
            continue

        if sym not in seen:
            seen.add(sym)
            out.append(sym)

        if len(out) >= _MAX_SYMBOLS:
            break

    return out

def _usage_text() -> str:
    return (
        "วิธีใช้:\n"
        "• `/crypto BTC`\n"
        "• `/crypto btc eth sol`\n"
        "• `/crypto $btc อีเธอเรียม โซลานา`\n"
        "รองรับหลายเหรียญคั่นเว้นวรรค และชื่อไทยยอดฮิตได้ครับ"
    )

def handle_crypto(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    try:
        symbols = _extract_symbols(user_text)

        if not symbols:
            send_message(chat_id, f"กรุณาระบุสัญลักษณ์เหรียญครับ\n\n{_usage_text()}")
            return

        # แจ้งสถานะกำลังค้นหา (ครั้งเดียว)
        send_message(chat_id, f"🔎 กำลังค้นหาราคาเหรียญ: {' '.join(symbols)}")
        send_typing_action(chat_id, "typing")

        # ดึงข้อมูลทีละเหรียญแบบทนทาน (กันเหรียญใดเหรียญหนึ่งล้มแล้วพังทั้งก้อน)
        results: List[str] = []
        for sym in symbols:
            try:
                send_typing_action(chat_id, "typing")
                msg = get_crypto_price_from_google(sym)  # คาดหวังข้อความ Markdown พร้อมราคา/เปลี่ยนแปลง
                if msg and isinstance(msg, str) and msg.strip():
                    results.append(msg.strip())
                else:
                    results.append(f"*{sym}*: ไม่พบข้อมูล")
            except Exception as e:
                # ไม่เผยรายละเอียดดิบกับผู้ใช้
                print(f"[handle_crypto] fetch error for {sym}: {e}")
                results.append(f"*{sym}*: ดึงข้อมูลไม่สำเร็จ")
        
        # รวมผลลัพธ์เป็นข้อความเดียว (ตัวห่อ send_message จะแบ่ง 4096 อัตโนมัติ)
        final_msg = "📈 *ราคาคริปโต*\n\n" + "\n\n".join(results)
        send_message(chat_id, final_msg, parse_mode="Markdown")

    except Exception as e:
        print(f"[handle_crypto] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลเหรียญ")
