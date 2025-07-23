# handlers/news.py

from utils.news_utils import get_news
from utils.message_utils import send_message

def handle_news(chat_id, query=None):
    """
    ดึงข่าวล่าสุด (หรือข่าวที่เกี่ยวข้องกับ query)
    :param chat_id: chat id ใน Telegram
    :param query: คำค้นหา (optional)
    """
    news_text = get_news(query=query)
    send_message(chat_id, news_text)
