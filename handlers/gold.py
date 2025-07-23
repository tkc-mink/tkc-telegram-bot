# handlers/gold.py
from utils.message_utils import send_message
from gold_utils import get_gold_price

def handle_gold(chat_id: int, user_text: str):
    send_message(chat_id, get_gold_price())
