# utils/news_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching the latest news using a reliable, internal search tool.
This version corrects a syntax error in the import statement.
"""
from __future__ import annotations
from typing import List

# Corrected the import from "Google Search" to "google_search"
try:
    from internal_tools import google_search
except ImportError:
    print("WARNING: 'internal_tools.google_search' not found. Using mock data for news.")
    class MockNewsResult:
        def __init__(self, title, link, snippet, source):
            self.title, self.link, self.snippet, self.source = title, link, snippet, source
    class MockSearchResults:
        def __init__(self, results):
            self.results = results
    def search_mock(queries=None, search_type=None):
        return [MockSearchResults([
            MockNewsResult("News Story 1", "https://example.com/1", "Summary of story 1...", "News Source A"),
            MockNewsResult("News Story 2", "https://example.com/2", "Summary of story 2...", "News Source B"),
            MockNewsResult("News Story 3", "https://example.com/3", "Summary of story 3...", "News Source C"),
        ])]
    google_search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_news(topic: str = "ข่าวล่าสุด") -> str:
    """
    Fetches the top 3 latest news articles on a given topic.
    """
    print(f"[News_Utils] Fetching news for topic: '{topic}'")
    
    try:
        # Use the corrected 'google_search' object
        search_results = google_search.search(queries=[topic], search_type='NEWS')
        
        if not search_results or not search_results[0].results:
            return f"❌ ขออภัยครับ ไม่พบข่าวในหัวข้อ '{topic}'"

        articles = search_results[0].results
        
        formatted_results = []
        for article in articles[:3]:
            title = article.title
            link = article.link
            snippet = article.snippet
            source = article.source
            
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
            return f"❌ ขออภัยครับ ไม่พบข่าวในหัวข้อ '{topic}'"

    except Exception as e:
        print(f"[News_Utils] An error occurred while fetching news: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคในการค้นหาข่าว"
