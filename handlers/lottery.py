# handlers/lottery.py
from utils.serp_utils import get_lottery_result
from utils.message_utils import send_message

def handle_lottery(chat_id, user_text):
    send_message(chat_id, get_lottery_result())
