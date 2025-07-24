import requests

def get_gold_price():
    # --- กำหนดค่า API ---
    GOLD_API_KEY = "goldapi-7ajusmdgypozu-io"  # นำ key ที่ได้มาใส่ตรงนี้
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
                    f"(ราคานี้คำนวณจากราคาสากล spot XAU/THB, ไม่รวมค่ากำเหน็จ)\n"
                    f"ดูราคาตลาดไทย: https://www.goldtraders.or.th/"
                )
        else:
            print("[gold_utils] GoldAPI status:", resp.status_code, resp.text)
    except Exception as e:
        print(f"[gold_utils] GoldAPI error: {e}")

    # Fallback mock ถ้า API ใช้ไม่ได้
    return (
        "📅 ราคาทองคำวันนี้ (ข้อมูลตัวอย่าง):\n"
        "ทองคำแท่ง: รับซื้อ 38,000 / ขายออก 38,100 บาท\n"
        "ทองรูปพรรณ: รับซื้อ 37,500 / ขายออก 38,600 บาท"
    )
