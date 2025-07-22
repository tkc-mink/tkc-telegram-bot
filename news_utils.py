import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def get_news(topic="ข่าว"):
    """
    ค้นหาข่าวล่าสุดจาก Google News ตาม keyword/topic ที่ระบุ
    แสดง headline + link + สรุปย่อ 2-3 ข่าว (ภาษาไทย)
    """
    try:
        url = f"https://www.google.com/search?q={quote(topic)}&tbm=nws&hl=th"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(resp.text, "lxml")
        items = []

        # Google News DOM เปลี่ยนบ่อย, รองรับ fallback
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
            if len(items) >= 3:
                break

        # Fallback: ถ้า Google ไม่เจอ หรือมีการ block
        if not items:
            # ลองใช้ภาษาอังกฤษ
            url_en = f"https://www.google.com/search?q={quote(topic)}&tbm=nws&hl=en"
            resp_en = requests.get(url_en, headers=headers, timeout=7)
            soup_en = BeautifulSoup(resp_en.text, "lxml")
            for n in soup_en.select("div.g"):
                title = n.select_one("h3")
                link = n.select_one("a")
                snippet = n.select_one("div.BNeawe.s3v9rd.AP7Wnd")
                if title and link:
                    url_news = link['href']
                    if url_news.startswith("/url?q="):
                        url_news = url_news.split("/url?q=")[1].split("&")[0]
                    summary = snippet.text.strip() if snippet else ""
                    items.append(f"• {title.text.strip()}\n{url_news}\n{summary}")
                if len(items) >= 3:
                    break

        if items:
            return "📰 ข่าวล่าสุด:\n" + "\n\n".join(items)
        return "ขออภัย ไม่พบข่าวที่เกี่ยวข้องจาก Google News ในขณะนี้"

    except Exception as e:
        print(f"[news_utils] error: {e}")
        return f"เกิดข้อผิดพลาดในการค้นหาข่าว: {str(e)}"
