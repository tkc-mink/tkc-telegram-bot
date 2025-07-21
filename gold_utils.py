# gold_utils.py
import requests
from bs4 import BeautifulSoup

def get_gold_price():
    try:
        url = "https://www.goldtraders.or.th/"
        resp = requests.get(url, timeout=7)
        soup = BeautifulSoup(resp.text, "html.parser")
        price_table = soup.select_one("table.table-price")
        if price_table:
            text = price_table.get_text(separator="\n", strip=True)
            return "ราคาทองคำ (อ้างอิงจาก goldtraders.or.th):\n" + text
        return "ขออภัย ไม่พบข้อมูลราคาทองจาก goldtraders.or.th"
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงราคาทอง: {str(e)}"
