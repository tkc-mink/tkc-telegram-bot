import requests
from bs4 import BeautifulSoup

def get_gold_price():
    try:
        url = "https://www.goldtraders.or.th/"
        resp = requests.get(url, timeout=7)
        soup = BeautifulSoup(resp.text, "html.parser")
        prices = []
        # หาตารางราคาทองคำแท่งและรูปพรรณ
        table = soup.find("table", class_="table-price")
        if not table:
            return "❌ ไม่พบข้อมูลราคาทองในขณะนี้"
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                if "ทองคำแท่ง" in cols[0]:
                    prices.append(f"ทองคำแท่ง: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
                elif "ทองรูปพรรณ" in cols[0]:
                    prices.append(f"ทองรูปพรรณ: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
        if prices:
            return "📅 ราคาทองคำวันนี้ (อ้างอิงสมาคมค้าทอง):\n" + "\n".join(prices)
        return "❌ ไม่พบราคาทองจากเว็บไซต์หลัก"
    except Exception as e:
        print(f"[gold_utils] error: {e}")
        return "❌ ไม่สามารถดึงข้อมูลราคาทองได้ในขณะนี้"
