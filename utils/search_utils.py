import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import json

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

def fetch_google_images(query, lang_out="th", max_results=3):
    """ค้นหารูปจาก Google Images (public, no API)"""
    headers = {"User-Agent": UA}
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=isch"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[fetch_google_images] HTTP {res.status_code}")
            return []
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        # Google ชอบเปลี่ยน selector บ่อย — ต้องดักกรณี alt="Image"
        for img in soup.select('img[src^="https"]'):
            src = img.get("src")
            if src and src.startswith("https") and ("gstatic.com" in src or "googleusercontent.com" in src):
                image_results.append(src)
            elif src and src.startswith("https") and len(src) > 80:
                image_results.append(src)
            if len(image_results) >= max_results:
                break
        if not image_results:
            print("[fetch_google_images] ไม่เจอรูปเลย")
        return image_results
    except Exception as e:
        print(f"[fetch_google_images] {e}")
        return []

def fetch_bing_images(query, max_results=3):
    """ค้นหารูปจาก Bing Images (public)"""
    headers = {"User-Agent": UA}
    url = f"https://www.bing.com/images/search?q={quote(query)}"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[fetch_bing_images] HTTP {res.status_code}")
            return []
        soup = BeautifulSoup(res.text, "lxml")
        image_results = []
        for img in soup.select('a.iusc'):
            m = img.get("m")
            if m:
                try:
                    meta = json.loads(m)
                    if "murl" in meta:
                        image_results.append(meta["murl"])
                except Exception as e:
                    print(f"[bing meta json error]: {e}")
            if len(image_results) >= max_results:
                break
        if not image_results:
            print("[fetch_bing_images] ไม่เจอรูปเลย")
        return image_results
    except Exception as e:
        print(f"[fetch_bing_images] {e}")
        return []

def fetch_duckduckgo_images(query, max_results=3):
    """ค้นหารูปจาก DuckDuckGo Images (public)"""
    headers = {"User-Agent": UA}
    try:
        session = requests.Session()
        url = f"https://duckduckgo.com/?q={quote(query)}&iar=images&iax=images&ia=images"
        res = session.get(url, headers=headers, timeout=10)
        vqd = None
        for line in res.text.splitlines():
            if "vqd=" in line:
                idx = line.find("vqd=")
                vqd = line[idx+5:idx+25]
                break
        if not vqd:
            print("[fetch_duckduckgo_images] ไม่พบ vqd token")
            return []
        api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote(query)}&vqd={vqd}"
        res = session.get(api_url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"[fetch_duckduckgo_images] API HTTP {res.status_code}")
            return []
        data = res.json()
        results = [img["image"] for img in data.get("results", [])]
        return results[:max_results]
    except Exception as e:
        print(f"[fetch_duckduckgo_images] {e}")
        return []

def robust_image_search(query, lang_out="th", max_results=3):
    """
    ค้นหารูปโดยลำดับ: Google > Bing > DuckDuckGo
    """
    results = fetch_google_images(query, lang_out=lang_out, max_results=max_results)
    if results:
        return results
    results = fetch_bing_images(query, max_results=max_results)
    if results:
        return results
    results = fetch_duckduckgo_images(query, max_results=max_results)
    if results:
        return results
    print("[robust_image_search] ไม่พบรูปจากทุก search")
    return []
