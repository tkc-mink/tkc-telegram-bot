# src/function_calling.py

import os
import json
from openai import OpenAI

from utils.weather_utils import get_weather_forecast
from utils.gold_utils    import get_gold_price
from utils.news_utils    import get_news
from utils.serp_utils    import (
    get_stock_info,
    get_oil_price,
    get_lottery_result,
    get_crypto_price,
)
from utils.bot_profile import adjust_bot_tone, bot_intro

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

SYSTEM_PROMPT = (
    "คุณคือบอทผู้ช่วยภาษาไทยชื่อ 'ชิบะน้อย' เป็นผู้ชาย แทนตัวเองว่า 'ผม' "
    "ตอบสุภาพ จริงใจ เป็นกันเอง ไม่ต้องพูดชื่อบอททุกข้อความ ยกเว้นถูกถามชื่อหรือทักครั้งแรก "
    "ถ้าผู้ใช้ถามชื่อ ให้แนะนำว่า 'ผมชื่อชิบะน้อยนะครับ' "
    "หากพบคำถามเกี่ยวกับอากาศ, ราคาทอง, ข่าว, หุ้น, น้ำมัน, หวย, คริปโต ให้เรียกฟังก์ชันที่ระบบมีให้"
)

def function_dispatch(fname, args):
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
    if not ctx:
        return []
    norm = []
    for item in ctx:
        if isinstance(item, dict) and "role" in item and "content" in item:
            norm.append(item)
        elif isinstance(item, str):
            norm.append({"role": "user", "content": item})
    return norm[-5:]

def process_with_function_calling(user_message: str, ctx=None, debug=False) -> str:
    try:
        # ถ้าคำถามเกี่ยวกับชื่อ ให้ตอบ intro ทันที
        if any(x in user_message.lower() for x in ["ชื่ออะไร", "คุณชื่ออะไร", "คุณคือใคร", "bot ชื่ออะไร", "/start"]):
            return bot_intro()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if ctx:
            norm_ctx = _normalize_context(ctx)
            messages.extend(norm_ctx)
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto"
        )
        msg = response.choices[0].message

        if msg.function_call:
            fname = msg.function_call.name
            args = json.loads(msg.function_call.arguments or "{}")
            result = function_dispatch(fname, args)

            messages.append({
                "role": "assistant",
                "function_call": {
                    "name": fname,
                    "arguments": json.dumps(args, ensure_ascii=False)
                }
            })
            messages.append({
                "role": "function",
                "name": fname,
                "content": result
            })

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
            return adjust_bot_tone(msg2.content.strip()) if msg2.content else adjust_bot_tone(result)

        answer = msg.content.strip() if msg.content else "❌ ไม่พบข้อความตอบกลับ"
        return adjust_bot_tone(answer)

    except Exception as e:
        print(f"[function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"

def summarize_text_with_gpt(text: str) -> str:
    try:
        messages = [
            {"role": "system", "content": "ช่วยสรุปเนื้อหานี้เป็นข้อความสั้นๆ ภาษาไทย"},
            {"role": "user", "content": text}
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        msg = response.choices[0].message
        return msg.content.strip() if msg.content else "❌ ไม่พบข้อความสรุป"
    except Exception as e:
        print(f"[summarize_text_with_gpt] {e}")
        return "❌ สรุปข้อความไม่สำเร็จ"
