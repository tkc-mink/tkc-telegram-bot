# search_utils.py
import requests
from bs4 import BeautifulSoup
from langdetect import detect
from urllib.parse import quote

def translate_query(query, lang_out="th"):
    """แปล query เป็นภาษาเป้าหมาย (ใช้ Google Translate API ฟรี)"""
    try:
        resp = requests.get(
            f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang_out}&dt=t&q={quote(query)}"
        )
        if resp.status_code == 200:
            return resp.json()[0][0][0]
        return query
    except Exception:
        return query

def fetch_google_web(query, lang_out="th", max_results=3):
    """ค้นหาข้อมูลเว็บทั่วไปจาก Google"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        results = []
        for g in soup.select("div.g"):
            title = g.select_one("h3")
            link = g.select_one("a")
            if title and link:
                url_result = link['href']
                if url_result.startswith("/url?q="):
                    url_result = url_result.split("/url?q=")[1].split("&")[0]
                url_result = url_result.split("&sa=")[0]
                results.append(f"• {title.text.strip()}\n{url_result}")
            if len(results) >= max_results:
                break
        # Featured Answer/Knowledge Panel
        if not results:
            featured = soup.select_one("div[data-attrid='wa:/description'] span")
            if featured:
                return [f"Google Featured Answer:\n{featured.text.strip()}"]
            return ["ไม่พบผลลัพธ์เว็บทั่วไปจาก Google ครับ"]
        return results
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหาเว็บ: {str(e)}"]

def fetch_google_news(query, lang_out="th", max_results=3):
    """ค้นหาข่าว Google News"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=nws"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        news_results = []
        for n in soup.select("div.g"):
            title = n.select_one("h3")
            link = n.select_one("a")
            snippet = n.select_one("div.BNeawe.s3v9rd.AP7Wnd")
            if title and link:
                url_news = link['href']
                if url_news.startswith("/url?q="):
                    url_news = url_news.split("/url?q=")[1].split("&")[0]
                summary = snippet.text.strip() if snippet else ""
                news_results.append(f"• {title.text.strip()}\n{url_news}\n{summary}")
            if len(news_results) >= max_results:
                break
        if not news_results:
            return ["ไม่พบข่าวจาก Google News ครับ"]
        return news_results
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหาข่าว: {str(e)}"]

def fetch_google_images(query, lang_out="th", max_results=3):
    """ค้นหารูปภาพจาก Google Images (ส่ง url รูปให้บอทใช้/preview)"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=isch"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        for img in soup.select("img"):
            src = img.get("src")
            # ดึงแต่ลิงก์รูปจริง ไม่เอารูปโลโก้/ไอคอน/empty
            if src and src.startswith("http"):
                image_results.append(src)
            if len(image_results) >= max_results:
                break
        if not image_results:
            return ["ไม่พบรูปภาพที่เกี่ยวข้องจาก Google Images ครับ"]
        # คืนค่ารูปแบบ markdown เพื่อให้บอท preview ได้ (หรือจะใช้ plain url ก็ได้)
        return [f"![image]({url})" if url else url for url in image_results]
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหารูปภาพ: {str(e)}"]

def smart_search(query, lang_out="th", max_results=3, enable_news=True, enable_images=True):
    """
    ค้นหาข้อมูลล่าสุดจาก Google (เว็บ+ข่าว+รูปภาพ)
    :param query: คำค้นหา
    :param lang_out: ภาษา (default 'th')
    :param max_results: จำนวนผลลัพธ์สูงสุด/หมวด
    :param enable_news: เปิด/ปิดการค้นหาข่าว
    :param enable_images: เปิด/ปิดการค้นหารูป
    :return: ข้อความ list[str] สำหรับสรุปส่งเข้า GPT-4o/บอท
    """
    try:
        # ตรวจจับภาษาและแปลเป็นไทย (หรือ lang_out)
        lang = detect(query)
        if lang != lang_out:
            query = translate_query(query, lang_out=lang_out)
        all_results = []
        # เว็บปกติ
        web_results = fetch_google_web(query, lang_out=lang_out, max_results=max_results)
        if web_results:
            all_results.append("🔎 **ผลลัพธ์จาก Google Search:**\n" + "\n\n".join(web_results))
        # ข่าว
        if enable_news:
            news_results = fetch_google_news(query, lang_out=lang_out, max_results=max_results)
            if news_results:
                all_results.append("📰 **ข่าวล่าสุด:**\n" + "\n\n".join(news_results))
        # รูปภาพ
        if enable_images:
            img_results = fetch_google_images(query, lang_out=lang_out, max_results=max_results)
            if img_results:
                all_results.append("🖼️ **ตัวอย่างรูปภาพ:**\n" + "\n".join(img_results))
        if not all_results:
            return ["ไม่พบข้อมูลจาก Google ครับ"]
        return all_results
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหาข้อมูล: {str(e)}"]
