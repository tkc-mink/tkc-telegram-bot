# src/utils/serp_utils.py

import requests

def get_stock_info(query):
    """
    ดึงราคาหุ้น (ปัจจุบัน mock, ต่อ API ได้ในอนาคต)
    """
    if "set" in query.lower():
        return "SET วันนี้: 1,234.56 (+4.56)"
    elif "ptt" in query.lower():
        return "PTT: 38.25 บาท (+0.25)"
    else:
        return "❌ ยังไม่รองรับหุ้นนี้"

def get_oil_price():
    """
    ดึงราคาน้ำมัน (mock)
    """
    return (
        "ราคาน้ำมันวันนี้:\n"
        "- ดีเซล: 30.94\n"
        "- แก๊สโซฮอล์ 95: 37.50\n"
        "- E20: 36.34 บาท"
    )

def get_lottery_result(date: str = None):
    """
    ดึงผลสลากกินแบ่งรัฐบาลจริง (API: lottoth-api)
    - ถ้าไม่ระบุ date จะดึงงวดล่าสุด
    - ระบุ date รูปแบบ 'YYYY-MM-DD'
    """
    api_url = "https://lottoth-api.vercel.app/api/latest"
    if date:
        api_url = f"https://lottoth-api.vercel.app/api/dates/{date}"
    try:
        res = requests.get(api_url, timeout=10)
        data = res.json()
        if not data or not data.get("data"):
            return "❌ ไม่พบข้อมูลผลสลาก (API)"
        d = data["data"]
        dt = d["date"]
        msg = (
            f"📅 ผลสลากกินแบ่งรัฐบาล งวดวันที่ {dt}\n"
            f"🏆 รางวัลที่ 1: {d['reward1']}\n"
            f"🔢 เลขหน้า 3 ตัว: {' '.join(d['front3'])}\n"
            f"🔢 เลขท้าย 3 ตัว: {' '.join(d['back3'])}\n"
            f"🎯 เลขท้าย 2 ตัว: {d['back2']}\n"
            f"(ข้อมูล: lottoth-api)"
        )
        return msg
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาด: {e}"

def get_crypto_price(coin):
    """
    ดึงราคาคริปโต (mock)
    """
    coin = coin.lower()
    if coin in ["btc", "bitcoin"]:
        return "Bitcoin (BTC): 2,350,000 บาท"
    elif coin in ["eth", "ethereum"]:
        return "Ethereum (ETH): 130,000 บาท"
    else:
        return f"❌ ยังไม่รองรับเหรียญ {coin.upper()}"

# --- วิธีต่อ API จริง (หุ้น/น้ำมัน/คริปโต) ---
# 1. หุ้นไทย: Finnomena API, SETTRADE API (ต้องสมัคร)
# 2. น้ำมัน: https://apigenerator.xyz/api/oil หรือ www.pttor.com
# 3. Crypto: CoinGecko API, CoinMarketCap API (ฟรี)
#
# (ถ้าต้องการโค้ดตัวอย่าง API จริงแต่ละตัว แจ้งชื่อฟีเจอร์มาได้เลย!)
