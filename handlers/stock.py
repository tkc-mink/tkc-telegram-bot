# handlers/stock.py
from utils.message_utils import send_message
from serp_utils import get_stock_info

def handle_stock(chat_id: int, user_text: str):
    # ตัวอย่าง: /stock AAPL
    parts = user_text.split()
    if len(parts) >= 2:
        symbol = parts[1]
    else:
        send_message(chat_id, "พิมพ์ /stock <symbol> เช่น /stock AAPL")
        return
    send_message(chat_id, get_stock_info(symbol))
