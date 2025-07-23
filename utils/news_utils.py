# news_utils.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

def get_news(topic="ข่าว"):
    """
    ดึงข่าวล่าสุด 3 ข่าวจาก Google News (ผลลัพธ์จะเป็นภาษาไทย/หัวข้อที่เจาะจง)
    """
    try:
        # ตั้งค่า User-Agent และ URL
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        url = f"https://www.google.com/search?q={quote(topic)}&tbm=nws&hl=th"
        resp = requests.get(url, headers=headers, timeout=8)
        if not resp.ok or not resp.text:
            return "❌ ไม่สามารถเชื่อมต่อ Google News ได้ในขณะนี้"

        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for div in soup.select("div.Gx5Zad.fP1Qef.xpd.EtOod.pkphOe"):
            # กล่องข่าว Google จะเปลี่ยน class ได้ ต้องมี fallback
            title_tag = div.select_one("div.BNeawe.vvjwJb.AP7Wnd")
            title = title_tag.text.strip() if title_tag else None

            link_tag = div.select_one("a")
            link = link_tag["href"] if link_tag and "href" in link_tag.attrs else ""
            # Google news: "/url?q=https://xxx"
            if link.startswith("/url?q="):
                link = link.split("/url?q=")[1].split("&")[0]
                link = unquote(link)

            summary_tag = div.select_one("div.BNeawe.s3v9rd.AP7Wnd")
            summary = summary_tag.text.strip() if summary_tag else ""

            if title and link:
                results.append(f"• {title}\n{link}\n{summary}")
            if len(results) >= 3:
                break

        # fallback: selector แบบเก่า
        if not results:
            for n in soup.select("div.g"):
                title = n.select_one("h3")
                link = n.select_one("a")
                snippet = n.select_one("div.BNeawe.s3v9rd.AP7Wnd")
                if title and link:
                    url_news = link['href']
                    if url_news.startswith("/url?q="):
                        url_news = url_news.split("/url?q=")[1].split("&")[0]
                        url_news = unquote(url_news)
                    summary = snippet.text.strip() if snippet else ""
                    results.append(f"• {title.text.strip()}\n{url_news}\n{summary}")
                if len(results) >= 3: break

        if results:
            return "📰 ข่าวล่าสุด:\n" + "\n\n".join(results)
        return "❌ ขอโทษ ไม่พบข่าวใหม่จาก Google News ในหัวข้อนี้"
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดในการค้นหาข่าว: {e}"
