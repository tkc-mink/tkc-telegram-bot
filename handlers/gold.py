from utils.gold_utils import get_gold_price
from utils.message_utils import send_message

def handle_gold(chat_id, user_text):
    try:
        gold_price = get_gold_price()
        if gold_price:
            send_message(chat_id, gold_price)
        else:
            send_message(chat_id, "ขออภัยค่ะ ไม่พบข้อมูลราคาทองขณะนี้")
    except Exception as e:
        print(f"[handle_gold] ERROR: {e}")
        send_message(chat_id, "❌ เกิดข้อผิดพลาดในการดึงข้อมูลราคาทองค่ะ")
