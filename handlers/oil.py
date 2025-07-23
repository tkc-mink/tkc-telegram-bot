# handlers/oil.py
from utils.serp_utils import get_oil_price
from utils.message_utils import send_message

def handle_oil(chat_id, user_text):
    send_message(chat_id, get_oil_price())
