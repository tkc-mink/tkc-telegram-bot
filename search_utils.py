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
            if src and src.startswith("http"):
                image_results.append(src)
            if len(image_results) >= max_results:
                break
        if not image_results:
            return ["ไม่พบรูปภาพที่เกี่ยวข้องจาก Google Images ครับ"]
        # ส่ง plain URL กลับ (เพื่อส่งเข้า sendPhoto ของ Telegram ได้ทันที)
        return [url for url in image_results if url]
    except Exception as e:
        return [f"เกิดข้อผิดพลาดในการค้นหารูปภาพ: {str(e)}"]
