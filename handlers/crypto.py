# handlers/crypto.py
from utils.serp_utils import get_crypto_price
from utils.message_utils import send_message

def handle_crypto(chat_id, user_text):
    parts = user_text.split()
    symbol = parts[1] if len(parts) > 1 else "BTC"
    send_message(chat_id, get_crypto_price(symbol))
