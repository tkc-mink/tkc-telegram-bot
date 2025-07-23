# handlers/main_handler.py

from handlers.history import *
from handlers.review import *
from handlers.weather import *
from handlers.doc import *
from handlers.image import *
from handlers.gold import *
from handlers.lottery import *
from handlers.stock import *
from handlers.crypto import *
from handlers.oil import *
# ... import อื่นๆ ที่จำเป็น

def handle_message(data):
    """
    ฟังก์ชันนี้จะรับ data จาก webhook (dict) แล้วตัดสินใจว่า
    จะโยนงานต่อไปที่ handler ไหน เช่น ตรวจสอบ command หรือประเภท message
    """
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user_text = msg.get("caption", "") or msg.get("text", "")

    # (ตัวอย่าง dispatch ฟีเจอร์)
    if user_text.startswith("/my_history"):
        # เรียกฟังก์ชันจาก history handler
        my_history(chat_id, user_text)
    elif user_text.startswith("/gold"):
        gold_price(chat_id, user_text)
    elif user_text.startswith("/lottery"):
        lottery_result(chat_id, user_text)
    elif user_text.startswith("/stock"):
        stock_price(chat_id, user_text)
    elif user_text.startswith("/crypto"):
        crypto_price(chat_id, user_text)
    elif user_text.startswith("/oil"):
        oil_price(chat_id, user_text)
    elif user_text.startswith("/weather"):
        weather(chat_id, user_text)
    elif "ขอรูป" in user_text:
        image_search(chat_id, user_text)
    # ... เพิ่มตามฟีเจอร์ของคุณ

    else:
        # default กรณีไม่ตรงเงื่อนไข
        pass  # หรือจะ reply ข้อความ default กลับไป

# หมายเหตุ: แต่ละฟังก์ชัน handler (เช่น gold_price, weather ฯลฯ) ต้องออกแบบให้รับ (chat_id, user_text)
# หรือถ้า handler เดิมของคุณออกแบบให้รับ telegram Update/context, สามารถ map/แปลงเองได้ (ตาม code base)
