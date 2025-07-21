import requests
from bs4 import BeautifulSoup
from langdetect import detect

# ตรวจจับว่าข้อความเป็นภาษาไทยหรือไม่
def is_thai(text):
    try:
        return detect(text) == "th"
    except:
        return False

# แปลไทย -> อังกฤษ (ใช้ LibreTranslate API)
def translate_to_en(text):
    url = "https://libretranslate.de/translate"
    data = {
        "q": text,
        "source": "th",
        "target": "en",
        "format": "text"
    }
    try:
        res = requests.post(url, data=data, timeout=5)
        return res.json().get("translatedText", text)
    except:
        return text

# ฟังก์ชันค้นหาผ่าน DuckDuckGo
def search_duckduckgo(query, max_results=3):
    url = "https://html.duckduckgo.com/html/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.post(url, data={"q": query}, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
    except requests.RequestException as e:
        return [f"เกิดข้อผิดพลาดในการค้นหา: {e}"]

    results = []
    for link in soup.find_all("a", attrs={"class": "result__a"}, limit=max_results):
        href = link.get("href")
        title = link.get_text()
        results.append(f"{title}\n{href}")
    return results

# รวมเป็น smart_search() ใช้ได้ทุกสถานการณ์
def smart_search(text):
    original_query = text
    text_lower = text.lower()

    # ค้นหาเฉพาะเว็บเฉพาะทาง
    if "youtube" in text_lower:
        query = original_query + " site:youtube.com"
    elif "wikipedia" in text_lower:
        query = original_query + " site:th.wikipedia.org"
    elif is_thai(original_query):
        query = original_query + " site:.th"
    else:
        query = original_query

    # แปลถ้าเป็นไทยและไม่ได้กำหนดโดเมน
    if is_thai(original_query) and "site:" not in query:
        translated = translate_to_en(original_query)
        if translated and translated != original_query:
            query = translated

    return search_duckduckgo(query)
