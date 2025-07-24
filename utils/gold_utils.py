import os
import requests

def get_gold_price() -> str:
    """
    คืนราคาทองคำสด (บาท) จาก GoldAPI.io (XAU/THB) พร้อม fallback ข้อมูลตัวอย่าง
    """
    # ดึง API KEY จาก ENV (อย่าฝัง key ไว้ในโค้ด)
    GOLD_API_KEY = os.getenv("GOLDAPI_KEY", "goldapi-7ajusmdgypozu-io")  # กำหนด default (ไม่ควรใช้ default ใน production)
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
                # 1 ออนซ์ทอง ≈ 31.1035 กรัม, 1 บาททอง ≈ 15.244 กรัม
                price_per_gram = price / 31.1035
                price_per_baht = price_per_gram * 15.244
                price_per_baht = int(price_per_baht // 10 * 10)  # ปัดเศษ
                return (
                    f"📅 ราคาทองคำอัพเดท (GoldAPI.io):\n"
                    f"ทองคำแท่งขายออก {price_per_baht:,} บาท/บาททอง\n"
                    f"(ราคานี้คำนวณจาก spot XAU/THB, ไม่รวมค่ากำเหน็จหรือ premium ตลาดไทย)\n"
                    f"ดูราคาตลาดไทย: https://www.goldtraders.or.th/"
                )
            else:
                print("[gold_utils] GoldAPI missing 'price' in response:", data)
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
