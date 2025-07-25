# handlers/lottery.py
from utils.lottery_utils import get_lottery_result
from utils.message_utils import send_message

def handle_lottery(chat_id, user_text):
    # รองรับ /lottery [วันที่/เดือน/ปี] เช่น /lottery 1 กรกฎาคม 2567
    parts = user_text.strip().split(" ", 1)
    if len(parts) == 2:
        query_date = parts[1]
    else:
        query_date = None
    result = get_lottery_result(query_date)
    send_message(chat_id, result, parse_mode="HTML")
