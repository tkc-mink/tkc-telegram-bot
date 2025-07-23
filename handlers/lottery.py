# handlers/lottery.py
from utils.message_utils import send_message
from serp_utils import get_lottery_result

def handle_lottery(chat_id: int, user_text: str):
    send_message(chat_id, get_lottery_result())
