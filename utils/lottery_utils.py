# utils/lottery_utils.py

import requests
from bs4 import BeautifulSoup
import re

def get_lottery_result(query_date=None):
    """
    ดึงผลสลากกินแบ่งรัฐบาลล่าสุด หรือย้อนหลังตามวันที่ที่ระบุ (รูปแบบ 1 กรกฎาคม 2567)
    :param query_date: วันที่ที่ต้องการ (str) เช่น "1 กรกฎาคม 2567" ถ้า None = งวดล่าสุด
    :return: ข้อความ HTML สำหรับ Telegram
    """
    try:
        base_url = "https://www.thairath.co.th/lottery/result"
        # --- กรณีระบุวัน/เดือน/ปี ---
        if query_date:
            # แปลง "1 กรกฎาคม 2567" เป็น "2024-07-01"
            import datetime
            import locale
            locale.setlocale(locale.LC_TIME, "th_TH.UTF-8")
            try:
                # ป้องกัน locale ไม่ได้บนบาง server (fallback manual map)
                th_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
                # แยกวัน เดือน ปี
                tokens = re.split(r"[\s/]", query_date.strip())
                if len(tokens) >= 3:
                    d, m, y = tokens[:3]
                    m_num = th_months.index(m) + 1 if m in th_months else int(m)
                    y = int(y)
                    if y > 2500: y -= 543  # แปลง พ.ศ. เป็น ค.ศ.
                    url = f"{base_url}/{y:04d}-{int(m_num):02d}-{int(d):02d}"
                else:
                    url = base_url
            except Exception as e:
                print("[LOTTO] Fallback locale:", e)
                url = base_url
        else:
            url = base_url

        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        # ----- หาวันที่ -----
        h1 = soup.find("h1")
        date_text = h1.text.strip() if h1 else "(ไม่พบวันที่)"
        # ----- รางวัลที่ 1 -----
        first_prize = soup.select_one(".lotto__result-row--first .lotto__result-number")
        first = first_prize.text.strip() if first_prize else "-"
        # ----- เลขท้าย 2 ตัว -----
        last2 = soup.select_one(".lotto__result-row--2digit .lotto__result-number")
        last2 = last2.text.strip() if last2 else "-"
        # ----- เลขหน้า 3 ตัว & เลขท้าย 3 ตัว -----
        threes = soup.select(".lotto__result-row--3digit .lotto__result-number")
        # ไทยรัฐจะเรียง เลขหน้า 3 ตัว, เลขท้าย 3 ตัว
        three_f, three_b = "-", "-"
        if len(threes) >= 2:
            three_f = threes[0].text.strip()
            three_b = threes[1].text.strip()
        msg = (
            f"📅 <b>{date_text}</b>\n"
            f"🏆 รางวัลที่ 1: <b>{first}</b>\n"
            f"🔢 เลขหน้า 3 ตัว: {three_f}\n"
            f"🔢 เลขท้าย 3 ตัว: {three_b}\n"
            f"🎯 เลขท้าย 2 ตัว: <b>{last2}</b>\n"
            f"\n(ข้อมูล: Thairath.co.th)"
        )
        return msg
    except Exception as e:
        print(f"[lottery_utils] error: {e}")
        return "❌ ไม่สามารถดึงผลสลากงวดนี้ได้ในขณะนี้"

# ทดสอบ
if __name__ == "__main__":
    print(get_lottery_result())
    print(get_lottery_result("16 กรกฎาคม 2567"))
