# utils/google_search_utils.py

import os
import requests

def google_search(query, num=3, search_type="web"):
    """
    ค้นหาข้อมูลหรือภาพจาก Google Custom Search API
    - search_type: "web" (ค้นเว็บ), "image" (ค้นภาพ)
    """
    API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
    CSE_ID  = os.getenv("GOOGLE_CSE_ID")
    if not API_KEY or not CSE_ID:
        return "❌ ยังไม่ได้ตั้งค่า GOOGLE_CSE_API_KEY หรือ GOOGLE_CSE_ID"

    params = {
        "key": API_KEY,
        "cx":  CSE_ID,
        "q":   query,
        "num": num
    }
    if search_type == "image":
        params["searchType"] = "image"

    try:
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
        if resp.status_code != 200:
            return f"❌ เกิดข้อผิดพลาด Google Search: {resp.status_code}"
        data = resp.json()
        items = data.get("items")
        if not items:
            return "ไม่พบผลลัพธ์ที่เกี่ยวข้อง"
        if search_type == "image":
            # ส่งภาพ url กลับ (เอาแค่ url จริง)
            return [item["link"] for item in items[:num]]
        else:
            # ส่งข้อความสรุปกลับ
            results = []
            for item in items[:num]:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                results.append(f"🔎 <b>{title}</b>\n{snippet}\n{link}")
            return "\n\n".join(results)
    except Exception as e:
        print(f"[google_search] {e}")
        return "❌ ดึงข้อมูล Google Search ไม่สำเร็จ"
