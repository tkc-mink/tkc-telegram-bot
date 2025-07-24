# handlers/search.py

from utils.google_search_utils import google_search
from utils.message_utils import send_message, send_photo

def handle_google_search(chat_id, user_text):
    """
    handler สำหรับค้นเว็บ Google แบบข้อความ ส่งผลลัพธ์กลับ Telegram
    """
    # รองรับทั้ง /search และ "ค้นหา ..." (ถ้าต้องการ)
    prefix = "/search"
    query = user_text
    if user_text.lower().startswith(prefix):
        query = user_text[len(prefix):].strip()
    elif user_text.startswith("ค้นหา"):
        query = user_text[3:].strip()
    if not query:
        send_message(chat_id, "❗️ พิมพ์ /search คำค้นหา เช่น /search รถยนต์ไฟฟ้า")
        return

    result = google_search(query, num=3, search_type="web")
    if not result or (isinstance(result, str) and not result.strip()):
        send_message(chat_id, "❌ ไม่พบผลลัพธ์สำหรับคำค้นหานี้")
        return

    send_message(chat_id, result, parse_mode="HTML")

def handle_google_image(chat_id, user_text):
    """
    handler สำหรับค้นหารูป Google Image ส่งรูปกลับ Telegram
    """
    prefix = "/image"
    query = user_text
    if user_text.lower().startswith(prefix):
        query = user_text[len(prefix):].strip()
    elif user_text.startswith("หารูป"):
        query = user_text[4:].strip()
    if not query:
        send_message(chat_id, "❗️ พิมพ์ /image คำค้นหา เช่น /image รถยนต์ไฟฟ้า")
        return

    imgs = google_search(query, num=2, search_type="image")
    if isinstance(imgs, list) and imgs:
        # ส่งทีละรูป (ส่งได้มากกว่า 1)
        for i, url in enumerate(imgs):
            if i == 0:
                send_photo(chat_id, url, caption=f"🔎 ผลการค้นหา: {query}")
            else:
                send_photo(chat_id, url)
    else:
        send_message(chat_id, imgs if isinstance(imgs, str) else "❌ ไม่พบรูปภาพที่เกี่ยวข้อง")

