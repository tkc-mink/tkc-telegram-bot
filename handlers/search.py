# handlers/search.py

from utils.google_search_utils import google_search
from utils.message_utils import send_message, send_photo

def handle_google_search(chat_id, user_text):
    """
    ค้นเว็บ Google แบบข้อความ
    """
    query = user_text.replace("/search", "", 1).strip()
    if not query:
        send_message(chat_id, "พิมพ์ /search คำค้นหา เช่น /search รถยนต์ไฟฟ้า")
        return
    result = google_search(query, num=3, search_type="web")
    send_message(chat_id, result, parse_mode="HTML")

def handle_google_image(chat_id, user_text):
    """
    ค้น Google Image
    """
    query = user_text.replace("/image", "", 1).strip()
    if not query:
        send_message(chat_id, "พิมพ์ /image คำค้นหา เช่น /image รถยนต์ไฟฟ้า")
        return
    imgs = google_search(query, num=2, search_type="image")
    if isinstance(imgs, list):
        for url in imgs:
            send_photo(chat_id, url)
    else:
        send_message(chat_id, imgs)
