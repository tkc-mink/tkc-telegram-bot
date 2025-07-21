# news_utils.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def get_news(topic="ข่าว"):
    try:
        url = f"https://www.google.com/search?q={quote(topic)}&tbm=nws&hl=th"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        for n in soup.select("div.g"):
            title = n.select_one("h3")
            link = n.select_one("a")
            snippet = n.select_one("div.BNeawe.s3v9rd.AP7Wnd")
            if title and link:
                url_news = link['href']
                if url_news.startswith("/url?q="):
                    url_news = url_news.split("/url?q=")[1].split("&")[0]
                summary = snippet.text.strip() if snippet else ""
                items.append(f"• {title.text.strip()}\n{url_news}\n{summary}")
            if len(items) >= 3: break
        if items:
            return "📰 ข่าวล่าสุด:\n" + "\n\n".join(items)
        return "ขออภัย ไม่พบข่าวจาก Google News ครับ"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการค้นหาข่าว: {str(e)}"
