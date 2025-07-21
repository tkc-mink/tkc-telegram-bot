import requests
from bs4 import BeautifulSoup
from langdetect import detect
from urllib.parse import quote

# ... ฟังก์ชัน translate_query, fetch_google_web, fetch_google_news, fetch_google_images ตามที่เขียนไปก่อนหน้า ...

def smart_search(query, lang_out="th", max_results=3, enable_news=True, enable_images=True):
    try:
        lang = detect(query)
        if lang != lang_out:
            query = translate_query(query, lang_out=lang_out)
        all_results = []
        web_results = fetch_google_web(query, lang_out=lang_out, max_results=max_results)
        if web_results:
            all_results.extend(web_results)
        if enable_news:
            news_results = fetch_google_news(query, lang_out=lang_out, max_results=max_results)
            if news_results:
                all_results.extend(news_results)
        if enable_images:
            img_results = fetch_google_images(query, lang_out=lang_out, max_results=max_results)
            if img_results:
                all_results.extend(img_results)
        if not all_results:
            return ["ไม่พบข้อมูลจาก Google ครับ"]
        return all_results
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหาข้อมูล: {str(e)}"]
