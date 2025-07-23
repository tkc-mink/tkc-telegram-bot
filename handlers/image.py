# handlers/image.py
from utils.message_utils import send_message
from utils.history_utils import log_message
from utils.search_utils import robust_image_search  # แก้ path

def handle_image(chat_id, user_text):
    user_id = str(chat_id)
    kw = user_text.strip()
    if kw == "":
        send_message(chat_id, "พิมพ์สิ่งที่ต้องการค้นหาภาพ เช่น 'ขอรูปรถกระบะ'")
        return

    imgs = robust_image_search(kw)
    if imgs:
        # ส่งไม่เกิน 3 รูป
        for url in imgs[:3]:
            send_message(chat_id, url)  # หรือใช้ send_photo ถ้าอยากส่งรูปจริง
        log_message(user_id, kw, "ส่งรูปภาพ (ดูในแชท)")
    else:
        send_message(chat_id, f"ไม่พบภาพสำหรับ '{kw}'")
