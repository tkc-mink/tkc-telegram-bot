import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import json

def fetch_google_images(query, lang_out="th", max_results=3):
    headers = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )}
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=isch"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        for img in soup.select('img[src^="https"]'):
            src = img.get("src")
            if src and src.startswith("https") and len(src) > 80:
                image_results.append(src)
            if len(image_results) >= max_results:
                break
        return image_results
    except Exception:
        return []

def fetch_bing_images(query, max_results=3):
    headers = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )}
    url = f"https://www.bing.com/images/search?q={quote(query)}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        for img in soup.select('a.iusc'):
            m = img.get("m")
            if m:
                meta = json.loads(m)
                if "murl" in meta:
                    image_results.append(meta["murl"])
            if len(image_results) >= max_results:
                break
        return image_results
    except Exception:
        return []

def fetch_duckduckgo_images(query, max_results=3):
    headers = {"User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )}
    url = f"https://duckduckgo.com/?q={quote(query)}&iar=images&iax=images&ia=images"
    try:
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=10)
        vqd = None
        for line in res.text.splitlines():
            if "vqd=" in line:
                idx = line.find("vqd=")
                vqd = line[idx+5:idx+25]
                break
        if not vqd:
            return []
        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote(query)}&vqd={vqd}"
        res = session.get(api_url, headers=headers, timeout=10)
        data = res.json()
        results = [img["image"] for img in data.get("results", [])]
        return results[:max_results]
    except Exception:
        return []

def robust_image_search(query, lang_out="th", max_results=3):
    # ลำดับ: Google → Bing → DuckDuckGo
    results = fetch_google_images(query, lang_out=lang_out, max_results=max_results)
    if results:
        return results
    results = fetch_bing_images(query, max_results=max_results)
    if results:
        return results
    results = fetch_duckduckgo_images(query, max_results=max_results)
    if results:
        return results
    return []   # ถ้าไม่มีเลย return []

