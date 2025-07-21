# search_utils.py
import requests
from bs4 import BeautifulSoup
from langdetect import detect
from urllib.parse import quote

def smart_search(query, lang_out="th", max_results=3):
    """
    ค้นหาข้อมูลล่าสุดจาก Google Search
    :param query: ข้อความค้นหา (string)
    :param lang_out: ภาษาแสดงผลที่ต้องการ (เช่น 'th' สำหรับไทย, 'en' สำหรับอังกฤษ)
    :param max_results: จำนวนผลลัพธ์สูงสุดที่ต้องการ (default 3)
    :return: รายการสรุปผล (list[str])
    """
    try:
        # 1. ตรวจสอบภาษาและแปลเป็นไทยถ้าไม่ใช่
        lang = detect(query)
        if lang != lang_out:
            resp = requests.get(
                f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang_out}&dt=t&q={quote(query)}"
            )
            if resp.status_code == 200:
                query = resp.json()[0][0][0]

        # 2. สร้าง headers เพื่อหลีกเลี่ยง Google block
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        # 3. ค้นหา Google Search
        url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}"
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return [f"ขออภัย ไม่สามารถเชื่อมต่อ Google ได้ (รหัส {res.status_code})"]

        soup = BeautifulSoup(res.text, "lxml")

        # 4. ดึงผลลัพธ์ (title + url)
        results = []
        for g in soup.select("div.g"):
            title = g.select_one("h3")
            link = g.select_one("a")
            if title and link:
                url = link['href']
                if url.startswith("/url?q="):
                    url = url.split("/url?q=")[1].split("&")[0]
                # ตัด query string ที่ติดท้าย url ออก (ถ้ามี)
                url = url.split("&sa=")[0]
                results.append(f"• {title.text.strip()}\n{url}")
            if len(results) >= max_results:
                break

        # 5. ถ้าไม่เจอผลลัพธ์ ดึง featured answer ถ้ามี
        if not results:
            featured = soup.select_one("div[data-attrid='wa:/description'] span")
            if featured:
                return [f"Google Featured Answer:\n{featured.text.strip()}"]
            return ["ไม่พบผลลัพธ์จาก Google ครับ"]

        return results

    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"]

