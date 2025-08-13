# handlers/crypto.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from utils.finance_utils import get_crypto_price_from_google
from utils.telegram_api import send_message

def handle_crypto(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id, user_name = user_info['profile']['user_id'], user_info['profile']['first_name']
    try:
        parts = user_text.split()
        if len(parts) < 2:
            send_message(chat_id, f"กรุณาระบุสัญลักษณ์เหรียญด้วยครับ เช่น `/crypto BTC`")
            return
        symbol = parts[1].upper()
        send_message(chat_id, f"🔎 กำลังค้นหาราคาเหรียญ {symbol}...")
        price_message = get_crypto_price_from_google(symbol)
        if price_message:
            send_message(chat_id, price_message, parse_mode="Markdown")
        else:
            send_message(chat_id, f"ขออภัยครับ ไม่พบข้อมูลสำหรับเหรียญ '{symbol}'")
    except Exception as e:
        print(f"[handle_crypto] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลเหรียญ")
