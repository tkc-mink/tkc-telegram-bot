# gold_utils.py

import requests
from datetime import datetime

GOLD_API_JSON = "https://goldtraders.or.th/backend/latestprice"

def get_gold_price() -> str:
    """
    ดึงราคาทองคำ 96.5% (บาทละ) จาก Goldtraders (JSON API)
    """
    try:
        resp = requests.get(GOLD_API_JSON, timeout=5)
        data = resp.json()
        # โครงสร้าง JSON: {"Date":"YYYY-MM-DD", "GoldPrice":[{"Type":"S96.5","Buy":..., "Sell":...},...]}
        date = data.get("Date", "")
        entries = data.get("GoldPrice", [])
        for item in entries:
            if item.get("Type") == "S96.5":
                buy  = item.get("Buy", 0)
                sell = item.get("Sell", 0)
                return (
                    f"📅 วันที่ {date}\n"
                    f"ทอง96.5% รับซื้อ {buy:,.2f} / ขายออก {sell:,.2f} บาท"
                )
        return "❌ ไม่พบราคาทอง 96.5% ในข้อมูลวันนี้"
    except Exception as e:
        print(f"[gold_utils] Error fetching gold price: {e}")
        return "❌ ไม่สามารถดึงข้อมูลราคาทองได้ในขณะนี้"
