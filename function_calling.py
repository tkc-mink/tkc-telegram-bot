import os
import json
from openai import OpenAI

from weather_utils import get_weather_forecast
from gold_utils    import get_gold_price
from news_utils    import get_news

# --- ฟังก์ชัน placeholder (ยังไม่ต้องใช้ SerpAPI) ---
def get_stock_info(query): return "❌ ยังไม่รองรับข้อมูลหุ้น"
def get_oil_price(): return "❌ ยังไม่รองรับราคาน้ำมัน"
def get_lottery_result(): return "❌ ยังไม่รองรับผลหวย"
def get_crypto_price(coin): return "❌ ยังไม่รองรับราคาคริปโต"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FUNCTIONS = [
    {
        "name": "get_weather_forecast",
        "description": "ดูพยากรณ์อากาศวันนี้หรืออากาศล่วงหน้าในไทย",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "ข้อความที่ผู้ใช้พิมพ์ เช่น อากาศที่โคราช หรือ พยากรณ์วันนี้"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "get_gold_price",
        "description": "ดูราคาทองคำประจำวัน",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_news",
        "description": "ดูข่าวหรือสรุปข่าววันนี้/ข่าวล่าสุด",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "หัวข้อที่ต้องการข่าว เช่น ข่าว, ข่าวเทคโนโลยี, ข่าวการเมือง"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "get_stock_info",
        "description": "ดูข้อมูลหุ้นวันนี้หรือหุ้นล่าสุดในไทย",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "ชื่อหุ้น, SET, หรือคำถามเกี่ยวกับหุ้น"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_oil_price",
        "description": "ดูราคาน้ำมันวันนี้",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_lottery_result",
        "description": "ผลสลากกินแบ่งรัฐบาลล่าสุด",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_crypto_price",
        "description": "ดูราคา bitcoin หรือเหรียญคริปโตอื่นๆ",
        "parameters": {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "ชื่อเหรียญเช่น bitcoin, btc, ethereum, eth, dogecoin"
                }
            },
            "required": ["coin"]
        }
    }
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
