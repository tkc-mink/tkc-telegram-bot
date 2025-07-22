import os
import json
from openai import OpenAI

from weather_utils import get_weather_forecast
from gold_utils    import get_gold_price
from news_utils    import get_news

# ถ้า serp_utils.py ยังไม่มี function พวกนี้ ให้สร้าง function เปล่า ๆ ไว้ก่อน
def get_stock_info(query): return "❌ ยังไม่รองรับข้อมูลหุ้น"
def get_oil_price(): return "❌ ยังไม่รองรับราคาน้ำมัน"
def get_lottery_result(): return "❌ ยังไม่รองรับผลหวย"
def get_crypto_price(coin): return "❌ ยังไม่รองรับราคาคริปโต"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FUNCTIONS = [
    # ... (เหมือนโค้ดคุณด้านบน) ...
]

SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI ภาษาไทยขององค์กรกลุ่มตระกูลชัย "
    "ตอบคำถามทั่วไปอย่างสุภาพ จริงใจ และเป็นประโยชน์ "
    "หากพบคำถามเกี่ยวกับอากาศ, ราคาทอง, ข่าว, หุ้น, น้ำมัน, หวย, คริปโต ให้เรียกฟังก์ชันที่ระบบมีให้ "
    "ห้ามตอบแทนถ้าฟังก์ชันสามารถจัดการได้"
)

def process_with_function_calling(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            functions=FUNCTIONS,
            function_call="auto"
        )
        msg = response.choices[0].message

        if msg.function_call:
            fname = msg.function_call.name
            args = json.loads(msg.function_call.arguments or "{}")
            if fname == "get_weather_forecast":
                return get_weather_forecast(text=args.get("text", ""))
            elif fname == "get_gold_price":
                return get_gold_price()
            elif fname == "get_news":
                return get_news(args.get("topic", "ข่าว"))
            elif fname == "get_stock_info":
                return get_stock_info(args.get("query", "หุ้น"))
            elif fname == "get_oil_price":
                return get_oil_price()
            elif fname == "get_lottery_result":
                return get_lottery_result()
            elif fname == "get_crypto_price":
                return get_crypto_price(args.get("coin", "bitcoin"))
            return "❌ ฟังก์ชันนี้ยังไม่รองรับในระบบ"
        return msg.content.strip() if msg.content else "❌ ไม่พบข้อความตอบกลับ"
    except Exception as e:
        print(f"[function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"
