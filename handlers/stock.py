# handlers/stock.py
# -*- coding: utf-8 -*-
"""
Handler for fetching and displaying stock information using the new, reliable Finance Utils.
"""
from __future__ import annotations
from typing import Dict, Any

# --- ส่วนที่เราแก้ไข ---
# 1. เปลี่ยนไป import ฟังก์ชันใหม่จาก finance_utils
from utils.finance_utils import get_stock_info_from_google
from utils.telegram_api import send_message

def handle_stock(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Parses the stock symbol, uses the new finance utility to fetch info, and sends it.
    """
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']

    print(f"[handle_stock] Received stock request from user {user_name} (ID: {chat_id})")

    try:
        parts = user_text.split()
        if len(parts) < 2:
            send_message(chat_id, f"กรุณาระบุชื่อย่อหุ้นที่ต้องการค้นหาด้วยครับคุณ {user_name}\nเช่น `/stock PTT` หรือ `หุ้น AOT`")
            return

        # ทำให้เป็นตัวพิมพ์ใหญ่และรองรับหุ้นไทย (.BK)
        symbol = parts[1].upper()
        if '.' not in symbol and len(symbol) <= 4: # สมมติฐาน: ถ้าไม่มี . และยาวไม่เกิน 4 ตัวอักษร อาจเป็นหุ้นไทย
             if not symbol.endswith(".BK"):
                  symbol += ".BK"
                  print(f"[handle_stock] Assuming Thai stock, appended .BK -> {symbol}")

        send_message(chat_id, f"🔎 กำลังค้นหาข้อมูลหุ้น {symbol} จาก Google Finance สักครู่นะครับ...")

        # 2. เรียกใช้ฟังก์ชันใหม่ที่เชื่อถือได้
        stock_info_message = get_stock_info_from_google(symbol)

        if stock_info_message:
            send_message(chat_id, stock_info_message, parse_mode="Markdown")
        else:
            send_message(chat_id, f"ขออภัยครับคุณ {user_name}, ผมไม่พบข้อมูลสำหรับหุ้น '{symbol}' ใน Google Finance ครับ ลองตรวจสอบชื่อย่ออีกครั้งนะครับ")

    except Exception as e:
        print(f"[handle_stock] An unhandled error occurred: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {user_name}, เกิดข้อผิดพลาดที่ไม่คาดคิดในการประมวลผลคำขอของคุณครับ")
