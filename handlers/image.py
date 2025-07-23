# handlers/image.py
from utils.message_utils import send_message, send_photo
from utils.usage_utils import check_and_increase_usage, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY, EXEMPT_USER_IDS
from search_utils import robust_image_search
from history_utils import log_message  # อยู่ใน utils.history_utils? ปรับ path ให้ตรง

def handle_image(chat_id: int, user_text: str):
    user_id = str(chat_id)
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY):
            send_message(chat_id, f"❌ ครบ {MAX_IMAGE_PER_DAY} รูปวันนี้แล้ว")
            return

    kw = user_text
    imgs = robust_image_search(kw)
    if imgs:
        for url in imgs[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์: {kw}")
        log_message(user_id, kw, "ส่งรูปภาพ (ดูในแชท)")
    else:
        send_message(chat_id, f"ไม่พบภาพสำหรับ '{kw}'")
