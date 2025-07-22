import requests
from datetime import datetime

def get_gold_price() -> str:
    try:
        resp = requests.get("https://goldtraders.or.th/backend/latestprice", timeout=5)
        data = resp.json()
        date = data.get("Date", "")
        entries = data.get("GoldPrice", [])
        for item in entries:
            if item.get("Type") == "S96.5":
                buy = item.get("Buy", 0)
                sell = item.get("Sell", 0)
                return (
                    f"📅 วันที่ {date}\n"
                    f"ทอง 96.5% รับซื้อ {buy:,.2f} / ขายออก {sell:,.2f} บาท"
                )
        return "❌ ไม่พบราคาทองในข้อมูลวันนี้"
    except Exception as e:
        print(f"[gold_utils] error: {e}")
        return "❌ ไม่สามารถดึงข้อมูลราคาทองได้ในขณะนี้"
