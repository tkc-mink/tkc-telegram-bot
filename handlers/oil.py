# handlers/oil.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from utils.finance_utils import get_oil_price_from_google
from utils.telegram_api import send_message

def handle_oil(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id, user_name = user_info['profile']['user_id'], user_info['profile']['first_name']
    try:
        send_message(chat_id, f"🔎 กำลังค้นหาราคาน้ำมันดิบ WTI และ Brent...")
        price_message = get_oil_price_from_google()
        if price_message:
            send_message(chat_id, price_message, parse_mode="Markdown")
        else:
            send_message(chat_id, "ขออภัยครับ ไม่พบข้อมูลราคาน้ำมันในขณะนี้")
    except Exception as e:
        print(f"[handle_oil] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับ เกิดข้อผิดพลาดในการดึงข้อมูลราคาน้ำมัน")
