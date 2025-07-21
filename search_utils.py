import requests
from bs4 import BeautifulSoup
import urllib.parse

def translate_th_to_en(text):
    # ใช้ API ฟรีของ LibreTranslate (หรือแปลแบบ simple fallback)
    url = "https://translate.argosopentech.com/translate"
    try:
        response = requests.post(url, json={
            "q": text,
            "source": "th",
            "target": "en",
            "format": "text"
        }, timeout=5)
        return response.json()['translatedText']
    except Exception:
        return text  # fallback หากแปลไม่ได้

def translate_en_to_th(text):
    # แปลกลับเป็นไทย
    url = "https://translate.argosopentech.com/translate"
    try:
        response = requests.post(url, json={
            "q": text,
            "source": "en",
            "target": "th",
            "format": "text"
        }, timeout=5)
        return response.json()['translatedText']
    except Exception:
        return text

def search_duckduckgo_translated(query_th, max_results=3):
    query_en = translate_th_to_en(query_th)
    search_url = "https://html.duckduckgo.com/html/"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        res = requests.post(search_url, data={"q": query_en}, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
    except requests.RequestException as e:
        return [f"⚠️ เกิดข้อผิดพลาดในการค้นหา: {e}"]

    results = []
    for link in soup.find_all("a", attrs={"class": "result__a"}, limit=max_results):
        href = link.get("href")
        title_en = link.get_text()
        title_th = translate_en_to_th(title_en)
        results.append(f"🔹 {title_th}\n{href}")

    if not results:
        return ["❌ ไม่พบผลลัพธ์ที่เกี่ยวข้อง"]
    return results
