# utils/lottery_utils.py
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def get_lottery_result(query_date=None):
    """
    ดึงผลสลากกินแบ่งรัฐบาลล่าสุด (หรือระบุวัน/เดือน/ปี เช่น '1 กรกฎาคม 2567')
    :param query_date: string วันที่ที่ต้องการ (ถ้า None = งวดล่าสุด)
    :return: ข้อความสำหรับส่งใน Telegram (HTML)
    """
    url = "https://www.sanook.com/news/lotto/"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ---- หาวันที่งวดล่าสุด ----
        header = soup.find("div", class_="lotto__result-title")
        date_text = header.get_text(strip=True) if header else "-"
        if query_date:
            # ตรวจสอบว่าผู้ใช้ระบุวันที่/เดือน/ปี ไหม
            # (Sanook มีเฉพาะงวดล่าสุด ถ้าอยากรองรับย้อนหลังควร scrape เว็บอื่นเพิ่ม)
            # กรณีนี้จะโชว์แค่งวดล่าสุด
            pass

        # ---- หารางวัล ----
        prize1 = soup.find("div", class_="result-lotto__number")
        first = prize1.get_text(strip=True) if prize1 else "-"

        last2 = soup.find("div", class_="result-lotto__2digits")
        last2 = last2.get_text(strip=True) if last2 else "-"

        threes = soup.find_all("div", class_="result-lotto__3digits")
        # [0] เลขหน้า 3 ตัว, [1] เลขท้าย 3 ตัว
        three_f, three_b = ("-", "-")
        if len(threes) >= 2:
            three_f = threes[0].get_text(strip=True)
            three_b = threes[1].get_text(strip=True)

        msg = (
            f"📅 <b>{date_text}</b>\n"
            f"🏆 รางวัลที่ 1: <b>{first}</b>\n"
            f"🔢 เลขหน้า 3 ตัว: {three_f}\n"
            f"🔢 เลขท้าย 3 ตัว: {three_b}\n"
            f"🎯 เลขท้าย 2 ตัว: <b>{last2}</b>\n"
            f"\n(ข้อมูล: Sanook.com)"
        )
        return msg

    except Exception as e:
        print(f"[lottery_utils] error: {e}")
        return "❌ ไม่สามารถดึงผลสลากงวดล่าสุดได้ในขณะนี้"

# ทดสอบเฉพาะโมดูล
if __name__ == "__main__":
    print(get_lottery_result())
