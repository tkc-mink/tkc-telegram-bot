# serp_utils.py

def get_stock_info(query):
    # สมมุติข้อมูล
    if "set" in query.lower():
        return "SET วันนี้: 1,234.56 (+4.56)"
    elif "ptt" in query.lower():
        return "PTT: 38.25 บาท (+0.25)"
    else:
        return "❌ ยังไม่รองรับหุ้นนี้"

def get_oil_price():
    return "ราคาน้ำมันวันนี้:\n- ดีเซล: 30.94\n- แก๊สโซฮอล์ 95: 37.50\n- E20: 36.34 บาท"

def get_lottery_result():
    return "ผลสลากกินแบ่งฯ ล่าสุด: 123456 (รางวัลที่ 1)\nเลขท้าย 2 ตัว: 78"

def get_crypto_price(coin):
    coin = coin.lower()
    if coin in ["btc", "bitcoin"]:
        return "Bitcoin (BTC): 2,350,000 บาท"
    elif coin in ["eth", "ethereum"]:
        return "Ethereum (ETH): 130,000 บาท"
    else:
        return f"❌ ยังไม่รองรับเหรียญ {coin.upper()}"
