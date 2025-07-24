import requests
from bs4 import BeautifulSoup

def get_gold_price():
    """
    คืนราคาทองวันนี้ (พยายามดึงจาก goldtraders.or.th ก่อน ถ้าไม่ได้ fallback ไป sanook)
    """
    # แหล่งที่ 1: สมาคมค้าทอง
    try:
        url1 = "https://www.goldtraders.or.th/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        resp1 = requests.get(url1, headers=headers, timeout=10)
        soup1 = BeautifulSoup(resp1.text, "html.parser")
        table1 = soup1.find("table", class_="table-price")
        if table1:
            prices = []
            for row in table1.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    if "ทองคำแท่ง" in cols[0]:
                        prices.append(f"ทองคำแท่ง: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
                    elif "ทองรูปพรรณ" in cols[0]:
                        prices.append(f"ทองรูปพรรณ: รับซื้อ {cols[1]} / ขายออก {cols[2]}")
            if prices:
                return "📅 ราคาทองคำวันนี้ (สมาคมค้าทอง):\n" + "\n".join(prices)
        else:
            print("[gold_utils] ไม่พบ table-price goldtraders")
    except Exception as e:
        print(f"[gold_utils] error goldtraders: {e}")

    # แหล่งที่ 2: Sanook (Fallback)
    try:
        url2 = "https://finance.sanook.com/economic/goldrate/"
        headers2 = {"User-Agent": "Mozilla/5.0"}
        resp2 = requests.get(url2, headers=headers2, timeout=10)
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        table2 = soup2.find("table", class_="tbl_gold")
        if table2:
            prices = []
            for row in table2.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    if "รับซื้อ" in cols[0] or "ขายออก" in cols[0]:
                        prices.append(f"{cols[0]} {cols[1]}")
            if prices:
                return "📅 ราคาทองวันนี้ (Sanook):\n" + "\n".join(prices)
        else:
            print("[gold_utils] ไม่พบ tbl_gold sanook")
    except Exception as e:
        print(f"[gold_utils] error sanook: {e}")

    # ถ้ายังไม่ได้ (mock fallback)
    return (
        "📅 ราคาทองคำวันนี้ (ข้อมูลตัวอย่าง):\n"
        "ทองคำแท่ง: รับซื้อ 38,000 / ขายออก 38,100 บาท\n"
        "ทองรูปพรรณ: รับซื้อ 37,500 / ขายออก 38,600 บาท"
    )
