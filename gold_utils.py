import requests
from bs4 import BeautifulSoup

def get_gold_price():
    try:
        url = "https://finance.sanook.com/economic/goldrate/"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="tbl_gold")
        if not table:
            print("[gold_utils] ไม่พบ table sanook")
            print(f"[gold_utils] resp.text: {resp.text[:300]}")
            return "❌ ไม่พบราคาทองจาก sanook"
        rows = table.find_all("tr")
        prices = []
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                if "รับซื้อ" in cols[0]:
                    prices.append(f"{cols[0]} {cols[1]}")
                elif "ขายออก" in cols[0]:
                    prices.append(f"{cols[0]} {cols[1]}")
        if prices:
            return "ราคาทองวันนี้ (Sanook):\n" + "\n".join(prices)
        return "❌ ไม่พบราคาทอง sanook"
    except Exception as e:
        print(f"[gold_utils] error: {e}")
        return "❌ ไม่สามารถดึงราคาทอง sanook ได้ในขณะนี้"
