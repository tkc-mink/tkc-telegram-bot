import requests
from bs4 import BeautifulSoup

def get_gold_price():
    try:
        url = "https://www.goldtraders.or.th/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table-price")
        if not table:
            # Debug: print html snippet (แนะนำให้คอมเมนต์ไว้เวลา deploy จริง)
            print("[gold_utils] ไม่พบ <table class='table-price'>")
            print(f"[gold_utils] resp.text: {resp.text[:300]}")
            return "❌ ไม่พบข้อมูลราคาทองในขณะนี้"

        rows = table.find_all("tr")
        prices = []
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                if "ทองคำแท่ง" in cols[0]:
                    prices.append(f"ทองคำแท่ง: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
                elif "ทองรูปพรรณ" in cols[0]:
                    prices.append(f"ทองรูปพรรณ: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
        if prices:
            return "📅 ราคาทองคำวันนี้ (อ้างอิงสมาคมค้าทอง):\n" + "\n".join(prices)
        else:
            # Debug: print html row content
            print("[gold_utils] ไม่พบราคาทองในตารางที่ระบุ")
            print(f"[gold_utils] table html: {str(table)[:300]}")
            return "❌ ไม่พบราคาทองจากเว็บไซต์หลัก"
    except Exception as e:
        print(f"[gold_utils] error: {e}")
        return "❌ ไม่สามารถดึงข้อมูลราคาทองได้ในขณะนี้"
