from utils.gold_utils import get_gold_price
from utils.message_utils import send_message

def handle_gold(chat_id, user_text):
    """
    handler ราคาทอง — ดึงราคาทองจาก gold_utils และส่งข้อความกลับให้ user
    """
    try:
        gold_price = get_gold_price()
        if gold_price and isinstance(gold_price, str):
            send_message(chat_id, gold_price)
        else:
            send_message(chat_id, "ขออภัยค่ะ ไม่พบข้อมูลราคาทองขณะนี้")
    except Exception as e:
        print(f"[handle_gold] ERROR: {e}")
        send_message(
            chat_id,
            "❌ ขณะนี้ไม่สามารถดึงข้อมูลราคาทองจากแหล่งหลักได้\n"
            "กรุณาลองใหม่อีกครั้ง หรือเช็คเว็บไซต์ goldtraders.or.th, sanook.com ด้วยตนเอง"
        )
