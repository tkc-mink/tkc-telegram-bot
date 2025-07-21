# search_utils.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def fetch_google_images(query, lang_out="th", max_results=3):
    """
    ดึง URL รูปภาพจาก Google Images (สำหรับ Telegram/Line OA/Facebook)
    Args:
        query (str): คำค้นหา เช่น "bridgestone 265/65R17"
        lang_out (str): ภาษา Google UI ('th', 'en' ฯลฯ)
        max_results (int): จำนวนรูปสูงสุด
    Returns:
        List[str]: url ของรูป (สำหรับส่งเข้า sendPhoto โดยตรง)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    }
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=isch"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        for img in soup.select('img[src^="https"]'):
            src = img.get("src")
            # กรองเฉพาะ url ที่ยาว (กัน logo/ไอคอน/placeholder)
            if src and src.startswith("https") and len(src) > 80:
                image_results.append(src)
            if len(image_results) >= max_results:
                break
        return image_results
    except Exception as e:
        return []
