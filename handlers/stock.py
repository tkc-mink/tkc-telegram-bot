# handlers/stock.py
from utils.serp_utils import get_stock_info
from utils.message_utils import send_message

def handle_stock(chat_id, user_text):
    parts = user_text.split()
    symbol = parts[1] if len(parts) > 1 else "AAPL"
    send_message(chat_id, get_stock_info(symbol))
