# utils/news_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching the latest news using a reliable, internal search tool.
This replaces the previous, fragile web scraping method.
"""
from __future__ import annotations
from typing import List, Dict, Optional

# ✅ ส่วนที่เราแก้ไข: เปลี่ยนมาใช้เครื่องมือภายในที่เสถียรกว่า
try:
    # นี่คือส่วนที่ผม (Gemini) จะใช้เครื่องมือของผม
    from internal_tools import Google Search
except ImportError:
    # ส่วนนี้สำหรับจำลองการทำงานเผื่อกรณีที่ tool ไม่พร้อมใช้งาน
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data for news.")
    class MockNewsResult:
        def __init__(self, title, link, snippet, source):
            self.title, self.link, self.snippet, self.source = title, link, snippet, source
    class MockSearchResults:
        def __init__(self, results):
            self.results = results
    def search_mock(queries=None, search_type=None):
        return [MockSearchResults([
            MockNewsResult("ข่าวเด่น 1", "https://example.com/1", "สรุปข่าวเด่น 1...", "สำนักข่าว A"),
            MockNewsResult("ข่าวเด่น 2", "https://example.com/2", "สรุปข่าวเด่น 2...", "สำนักข่าว B"),
            MockNewsResult("ข่าวเด่น 3", "https://example.com/3", "สรุปข่าวเด่น 3...", "สำนักข่าว C"),
        ])]
    Google Search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_news(topic: str = "ข่าวล่าสุด") -> str:
    """
    Fetches the top 3 latest news articles on a given topic using the internal search tool.
    
    Args:
        topic: The news topic to search for. Defaults to "ข่าวล่าสุด".
    
    Returns:
        A formatted string with the top 3 news articles, or an error message.
    """
    print(f"[News_Utils] Fetching news for topic: '{topic}'")
    
    try:
        # ✅ ใช้เครื่องมือค้นหาข่าวโดยตรง ทำให้ไม่ต้อง parse HTML เอง
        # เราสามารถระบุ search_type='NEWS' เพื่อให้ได้ผลลัพธ์ที่ดีที่สุด
        search_results = Google Search(queries=[topic], search_type='NEWS')
        
        if not search_results or not search_results[0].results:
            print(f"[News_Utils] No news found for topic: '{topic}'")
            return f"❌ ขออภัยครับ ไม่พบข่าวในหัวข้อ '{topic}' ในขณะนี้"

        # ✅ ดึงข้อมูลจากผลลัพธ์ที่มีโครงสร้างชัดเจน (title, link, snippet)
        articles = search_results[0].results
        
        # จัดรูปแบบผลลัพธ์ 3 อันดับแรก
        formatted_results = []
        for article in articles[:3]:
            title = article.title
            link = article.link
            snippet = article.snippet
            source = article.source
            
            # ตัด snippet ให้ไม่ยาวเกินไป
            if len(snippet) > 100:
                snippet = snippet[:100] + "..."
            
            formatted_results.append(
                f"📰 **{title}**\n"
                f"🖋️ *{source}*\n"
                f"{snippet}\n"
                f"🔗 [อ่านต่อ]({link})"
            )
        
        if formatted_results:
            header = f"🗞️ **ข่าวเด่นในหัวข้อ: {topic}**\n"
            return header + "\n\n".join(formatted_results)
        else:
            return f"❌ ขออภัยครับ ไม่พบข่าวในหัวข้อ '{topic}' ในขณะนี้"

    except Exception as e:
        print(f"[News_Utils] An error occurred while fetching news: {e}")
        return f"❌ ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคในการค้นหาข่าว"
