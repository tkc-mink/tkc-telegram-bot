# handlers/crypto.py
from utils.message_utils import send_message
from serp_utils import get_crypto_price

def handle_crypto(chat_id: int, user_text: str):
    parts = user_text.split()
    symbol = parts[1] if len(parts) >= 2 else "BTC"
    send_message(chat_id, get_crypto_price(symbol))
