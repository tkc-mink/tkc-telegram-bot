# function_calling.py

import os
import json
from openai import OpenAI

# เปลี่ยนเป็น import จากโฟลเดอร์ utils
from utils.weather_utils import get_weather_forecast
from utils.gold_utils    import get_gold_price
from utils.news_utils    import get_news
from utils.serp_utils    import (
    get_stock_info,
    get_oil_price,
    get_lottery_result,
    get_crypto_price,
)

# สร้าง client ด้วย API key จาก ENV
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# กำหนด metadata ของฟังก์ชันที่ GPT จะเรียกใช้
FUNCTIONS = [
    {
        "name": "get_weather_forecast",
        "description": "ดูพยากรณ์อากาศวันนี้หรืออากาศล่วงหน้าในไทย",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "ข้อความที่ผู้ใช้พิมพ์"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "get_gold_price",
        "description": "ดูราคาทองคำประจำวัน",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_news",
        "description": "ดูข่าวหรือสรุปข่าววันนี้/ข่าวล่าสุด",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "หัวข้อข่าว"}
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
                "query": {"type": "string", "description": "ชื่อหุ้น หรือ SET"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_oil_price",
        "description": "ดูราคาน้ำมันวันนี้",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_lottery_result",
        "description": "ผลสลากกินแบ่งรัฐบาลล่าสุด",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_crypto_price",
        "description": "ดูราคา bitcoin หรือเหรียญคริปโต",
        "parameters": {
            "type": "object",
            "properties": {
                "coin": {"type": "string", "description": "ชื่อเหรียญ"}
            },
            "required": ["coin"]
        }
    },
]

# ข้อความ system prompt
SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI ภาษาไทยขององค์กรกลุ่มตระกูลชัย "
    "ตอบคำถามทั่วไปอย่างสุภาพ จริงใจ และเป็นประโยชน์ "
    "หากพบคำถามเกี่ยวกับอากาศ, ราคาทอง, ข่าว, หุ้น, น้ำมัน, หวย, คริปโต ให้เรียกฟังก์ชันที่ระบบมีให้"
)

def function_dispatch(fname, args):
    """
    Map function name from GPT to actual Python function
    """
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
    else:
        return "❌ ฟังก์ชันนี้ยังไม่รองรับในระบบ"

def _normalize_context(ctx):
    """
    Ensure context is a list of message-dict (role/content)
    """
    if not ctx:
        return []
    norm = []
    for item in ctx:
        if isinstance(item, dict) and "role" in item and "content" in item:
            norm.append(item)
        elif isinstance(item, str):
            norm.append({"role": "user", "content": item})
    # เก็บเฉพาะ context 5 ข้อความล่าสุด
    return norm[-5:]

def process_with_function_calling(user_message: str, ctx=None, debug=False) -> str:
    """
    Function calling + multi-turn context-aware, fallback GPT answer.
    """
    try:
        # 1. เตรียม conversation context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if ctx:
            norm_ctx = _normalize_context(ctx)
            messages.extend(norm_ctx)
        messages.append({"role": "user", "content": user_message})

        # 2. เรียก GPT ครั้งแรก ให้เลือกเรียก function อัตโนมัติ
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto"
        )
        msg = response.choices[0].message

        # 3. ถ้า GPT สั่งเรียก function ให้ dispatch แล้วเรียก GPT รอบสองสรุปผล
        if msg.function_call:
            fname = msg.function_call.name
            args = json.loads(msg.function_call.arguments or "{}")
            result = function_dispatch(fname, args)

            # เพิ่มข้อความที่ bot เรียก function
            messages.append({
                "role": "assistant",
                "function_call": {
                    "name": fname,
                    "arguments": json.dumps(args, ensure_ascii=False)
                }
            })
            # เพิ่มข้อความที่ function ตอบกลับ
            messages.append({
                "role": "function",
                "name": fname,
                "content": result
            })

            # เรียก GPT อีกครั้งโดยไม่ต้องเรียก function แล้ว
            response2 = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                functions=FUNCTIONS,
                function_call="none"
            )
            msg2 = response2.choices[0].message
            if debug:
                print("=== FUNC-CALL CONTEXT ===")
                print(json.dumps(messages, ensure_ascii=False, indent=2))
                print("=== FUNC-CALL RESPONSE ===")
                print(msg2.content)
            return msg2.content.strip() if msg2.content else result

        # 4. มิฉะนั้น ให้ตอบกลับปกติ
        return msg.content.strip() if msg.content else "❌ ไม่พบข้อความตอบกลับ"

    except Exception as e:
        # กรณี error
        print(f"[function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"
