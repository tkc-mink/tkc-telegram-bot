# handlers/oil.py
from utils.message_utils import send_message
from serp_utils import get_oil_price

def handle_oil(chat_id: int, user_text: str):
    send_message(chat_id, get_oil_price())
