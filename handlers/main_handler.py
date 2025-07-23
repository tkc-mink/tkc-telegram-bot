# handlers/main_handler.py
import traceback
from utils.message_utils import send_message

# mapping คำสั่ง -> ฟังก์ชัน (lazy import)
def _dispatch(cmd: str):
    if cmd == "history":
        from handlers.history import handle_history
        return handle_history
    if cmd == "gold":
        from handlers.gold import handle_gold
        return handle_gold
    if cmd == "lottery":
        from handlers.lottery import handle_lottery
        return handle_lottery
    if cmd == "stock":
        from handlers.stock import handle_stock
        return handle_stock
    if cmd == "crypto":
        from handlers.crypto import handle_crypto
        return handle_crypto
    if cmd == "oil":
        from handlers.oil import handle_oil
        return handle_oil
    if cmd == "weather":
        from handlers.weather import handle_weather
        return handle_weather
    if cmd == "image":
        from handlers.image import handle_image
        return handle_image
    if cmd == "review":
        from handlers.review import handle_review
        return handle_review
    if cmd == "doc":
        from handlers.doc import handle_doc
        return handle_doc
    return None

def handle_message(data: dict):
    msg       = data.get("message", {}) or {}
    chat_id   = msg.get("chat", {}).get("id")
    user_text = (msg.get("caption") or msg.get("text") or "").strip()
    low       = user_text.lower()

    if not chat_id:
        return

    try:
        # document ก่อน (กรณีไม่มีข้อความ แต่ส่งไฟล์)
        if msg.get("document"):
            _dispatch("doc")(chat_id, msg)
            return

        if   low.startswith("/my_history"):   _dispatch("history")(chat_id, user_text)
        elif low.startswith("/gold"):         _dispatch("gold")(chat_id, user_text)
        elif low.startswith("/lottery"):      _dispatch("lottery")(chat_id, user_text)
        elif low.startswith("/stock"):        _dispatch("stock")(chat_id, user_text)
        elif low.startswith("/crypto"):       _dispatch("crypto")(chat_id, user_text)
        elif low.startswith("/oil"):          _dispatch("oil")(chat_id, user_text)
        elif low.startswith("/weather") or "อากาศ" in low:
                                              _dispatch("weather")(chat_id, user_text)
        elif "ขอรูป" in low or low.startswith("/image"):
                                              _dispatch("image")(chat_id, user_text)
        elif low.startswith("/review"):       _dispatch("review")(chat_id, user_text)
        elif low.startswith("/doc"):          _dispatch("doc")(chat_id, msg)
        elif low.startswith("/start") or low.startswith("/help"):
            send_message(chat_id,
                "ยินดีต้อนรับสู่ TKC Bot 🦊\n\n"
                "- /my_history ประวัติ\n- /gold ราคาทอง\n- /lottery ผลสลาก\n"
                "- /stock <symbol>\n- /crypto <symbol>\n- /oil ราคาน้ำมันโลก\n"
                "- /weather อากาศ (ต้องแชร์ location ก่อน)\n- /review ให้คะแนนบอท\n"
                "- ส่งเอกสาร (PDF/Word/Excel/PPT/TXT) เพื่อสรุป"
            )
        elif user_text == "":
            send_message(chat_id, "⚠️ กรุณาพิมพ์ข้อความ หรือใช้ /help")
        else:
            send_message(chat_id, "❓ ไม่เข้าใจคำสั่ง ลองใหม่ หรือพิมพ์ /help")
    except Exception as e:
        send_message(chat_id, f"❌ ระบบขัดข้อง: {e}")
        print(traceback.format_exc())
