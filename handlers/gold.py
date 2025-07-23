# handlers/gold.py
from utils.gold_utils import get_gold_price
from utils.message_utils import send_message

def handle_gold(chat_id, user_text):
    send_message(chat_id, get_gold_price())
