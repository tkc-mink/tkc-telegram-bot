# handlers/history.py
from utils.history_utils import get_user_history   # <== แก้ path
from utils.message_utils import send_message

def handle_history(chat_id: int, user_text: str) -> None:
    user_id = str(chat_id)
    logs = get_user_history(user_id, limit=10)
    if not logs:
        send_message(chat_id, "🔍 คุณยังไม่มีประวัติการใช้งานเลยครับ")
        return

    pieces = []
    for l in logs:
        date = l.get("date", "")
        q = l.get("q", "")
        a = l.get("a", "")
        ans_line = f"💬 {a}" if a else ""
        pieces.append(f"🗓️ {date}\n❓{q}\n{ans_line}")

    send_message(chat_id, "📜 ประวัติคำถามย้อนหลัง 10 รายการ:\n\n" + "\n\n".join(pieces))
