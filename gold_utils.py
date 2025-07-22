# gold_utils.py
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
            return "📅 ราคาทองคำวันนี้ (สมาคมค้าทอง):\n" + "\n".join(prices)
        else:
            return "❌ ไม่พบราคาทองจากเว็บไซต์หลัก"
    except Exception as e:
        return "❌ ไม่สามารถดึงข้อมูลราคาทองได้ในขณะนี้"
