import os
import requests
from bs4 import BeautifulSoup

def get_gold_price() -> str:
    """
    คืนราคาทองคำวันนี้ (สมาคมค้าทองคำ ถ้า scrape ไม่ได้จะ fallback GoldAPI.io)
    """
    # ---------- 1) Scrape ราคาจากสมาคมค้าทอง ----------
    try:
        url = "https://www.goldtraders.or.th/"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="table-price")
        prices = []
        if table:
            for row in table.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    if "ทองคำแท่ง" in cols[0]:
                        prices.append(f"ทองคำแท่ง: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
                    elif "ทองรูปพรรณ" in cols[0]:
                        prices.append(f"ทองรูปพรรณ: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
            if prices:
                return (
                    "📅 ราคาทองวันนี้ (สมาคมค้าทองคำ):\n"
                    + "\n".join(prices)
                    + "\n\nดูกราฟและข้อมูลละเอียด: https://www.goldtraders.or.th/"
                )
        else:
            print("[gold_utils] ไม่พบ table-price goldtraders")
    except Exception as e:
        print(f"[gold_utils] error goldtraders: {e}")

    # ---------- 2) Fallback ไป GoldAPI.io (spot) ----------
    GOLD_API_KEY = os.getenv("GOLDAPI_KEY")
    if GOLD_API_KEY:
        url = "https://www.goldapi.io/api/XAU/THB"
        headers = {
            "x-access-token": GOLD_API_KEY,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                price = data.get("price")
                if price:
                    # 1 ออนซ์ ≈ 31.1035 กรัม, 1 บาททอง ≈ 15.244 กรัม
                    price_per_gram = price / 31.1035
                    price_per_baht = price_per_gram * 15.244
                    price_per_baht = int(price_per_baht // 10 * 10)
                    return (
                        f"📅 ราคาทองคำอัพเดท (GoldAPI.io):\n"
                        f"ทองคำแท่งขายออก {price_per_baht:,} บาท/บาททอง\n"
                        f"(ราคานี้คำนวณจาก spot XAU/THB, ไม่รวมค่ากำเหน็จหรือ premium ตลาดไทย)\n"
                        f"ดูราคาตลาดไทย: https://www.goldtraders.or.th/"
                    )
        except Exception as e:
            print(f"[gold_utils] GoldAPI error: {e}")

    # ---------- 3) Fallback mock ถ้าไม่มี api key หรือ error ----------
    return (
        "📅 ราคาทองคำวันนี้ (ข้อมูลตัวอย่าง):\n"
        "ทองคำแท่ง: รับซื้อ 38,000 / ขายออก 38,100 บาท\n"
        "ทองรูปพรรณ: รับซื้อ 37,500 / ขายออก 38,600 บาท"
    )
