# handlers/news.py
# -*- coding: utf-8 -*-

from utils.news_utils import get_news
from utils.message_utils import send_message


def handle_news(chat_id: int, query: str | None) -> None:
    """
    ใช้:
    - /news
    - /news หุ้นไทย
    """
    try:
        q = (query or "").strip()
        news_text = get_news(q or "ข่าวสำคัญวันนี้")
        send_message(chat_id, news_text, parse_mode="HTML")
    except Exception as e:
        send_message(chat_id, f"❌ ดึงข่าวไม่สำเร็จ: {e}")
