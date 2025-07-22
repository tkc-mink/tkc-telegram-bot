import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_gold_price():
    try:
        url = "https://finance.sanook.com/economic/goldrate/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="tbl_gold")

        # เช็คว่าเจอ table หรือไม่
        if not table:
            print("[gold_utils] ไม่พบ table sanook")
            return "❌ ไม่พบราคาทองจาก sanook ในขณะนี้"

        # หาวันที่อัปเดตล่าสุด
        dateinfo = ""
        dateblock = soup.find("div", class_="date-update")
        if dateblock:
            dateinfo = dateblock.get_text(strip=True)
        else:
            # fallback: วันปัจจุบัน
            dateinfo = datetime.now().strftime("%d/%m/%Y")

        prices = []
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            # รูปแบบปกติ: [ประเภท, รับซื้อ, ราคา, ขายออก, ราคา]
            if len(cols) >= 5 and ("ทองคำแท่ง" in cols[0] or "ทองรูปพรรณ" in cols[0]):
                prices.append(
                    f"{cols[0]}:\n"
                    f"• รับซื้อ: {cols[2]}\n"
                    f"• ขายออก: {cols[4]}"
                )
            # รูปแบบสำรอง (กรณี DOM เปลี่ยน)
            elif len(cols) >= 3 and ("รับซื้อ" in cols[0] or "ขายออก" in cols[0]):
                prices.append(f"{cols[0]} {cols[1]} {cols[2]}")

        # Fallback ถ้าไม่มีข้อมูลเลย
        if not prices:
            # ลองดึงทุกแถวที่มี "รับซื้อ"/"ขายออก" เผื่อ DOM เปลี่ยน
            for row in table.find_all("tr"):
                txt = " ".join([c.get_text(strip=True) for c in row.find_all("td")])
                if "รับซื้อ" in txt or "ขายออก" in txt:
                    prices.append(txt)

        # แสดงผล
        if prices:
            out = "📊 ราคาทองวันนี้ (Sanook)\n"
            out += f"อัปเดต: {dateinfo}\n"
            out += "\n".join(prices)
            return out
        else:
            return "❌ ไม่พบราคาทอง sanook (ข้อมูลในเว็บอาจเปลี่ยน)"

    except Exception as e:
        print(f"[gold_utils] error: {e}")
        return "❌ ไม่สามารถดึงราคาทอง sanook ได้ในขณะนี้"
