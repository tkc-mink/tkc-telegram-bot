# handlers/crypto.py
# -*- coding: utf-8 -*-

from utils.serp_utils import get_crypto_price
from utils.message_utils import send_message


def _pick_symbol_from_text(text: str) -> str:
    t = (text or "").strip().lower()
    # เดารหัสเหรียญจากข้อความผู้ใช้
    if "eth" in t or "ethereum" in t:
        return "ETH"
    if "doge" in t:
        return "DOGE"
    if "bnb" in t:
        return "BNB"
    if "sol" in t or "solana" in t:
        return "SOL"
    # ดีฟอลต์เป็น BTC
    return "BTC"


def handle_crypto(chat_id: int, user_text: str) -> None:
    """
    ตัวอย่างข้อความ:
    - /crypto
    - /crypto btc
    - ราคา eth วันนี้
    """
    try:
        parts = (user_text or "").strip().split()
        symbol = parts[1].upper() if len(parts) > 1 else _pick_symbol_from_text(user_text)
        reply = get_crypto_price(symbol)  # ควรคืน string พร้อมจัดรูปแบบแล้ว
        send_message(chat_id, reply, parse_mode="HTML")
    except Exception as e:
        send_message(chat_id, f"❌ ดึงราคาเหรียญไม่สำเร็จ: {e}")
