# search_utils.py

import requests
from bs4 import BeautifulSoup
from langdetect import detect

def smart_search(query):
    try:
        lang = detect(query)
        if lang != "th":
            trans_resp = requests.get(
                f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=th&dt=t&q={query}"
            )
            query = trans_resp.json()[0][0][0]

        url = f"https://www.google.com/search?q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "lxml")

        results = []
        for g in soup.select("div.g"):
            title = g.select_one("h3")
            link = g.select_one("a")
            if title and link:
                results.append(f"{title.text.strip()}\n{link['href']}")
            if len(results) >= 5:
                break

        return results

    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"]
