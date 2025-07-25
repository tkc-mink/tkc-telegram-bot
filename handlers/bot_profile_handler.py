from utils.bot_profile import set_bot_profile, get_bot_profile
from utils.message_utils import send_message

def handle_set_nickname(chat_id, user_text):
    nickname = user_text.replace("/set_nickname", "").strip()
    if nickname:
        set_bot_profile(nickname=nickname)
        send_message(chat_id, f"✅ เปลี่ยนชื่อเล่นบอทเป็น {nickname} แล้วครับ")
    else:
        send_message(chat_id, "❌ กรุณาระบุชื่อเล่นที่ต้องการหลังคำสั่ง /set_nickname")

def handle_set_gender(chat_id, user_text):
    txt = user_text.replace("/set_gender", "").strip().lower()
    if txt in ["male", "ชาย"]:
        set_bot_profile(gender="male", self_pronoun="ผม")
        send_message(chat_id, "✅ เปลี่ยนเพศบอทเป็นชาย เรียกตัวเองว่า 'ผม'")
    elif txt in ["female", "หญิง"]:
        set_bot_profile(gender="female", self_pronoun="หนู")
        send_message(chat_id, "✅ เปลี่ยนเพศบอทเป็นหญิง เรียกตัวเองว่า 'หนู'")
    else:
        send_message(chat_id, "❌ กรณีใส่ male/ชาย หรือ female/หญิง เท่านั้น เช่น /set_gender ชาย")
