# src/function_calling.py
# -*- coding: utf-8 -*-

import os
import json
from typing import List, Dict, Any, Optional
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

# ---------- OpenAI Client (ไม่มี proxies ในโค้ด) ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------- Tools (Function Calling แบบใหม่) ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "ดูพยากรณ์อากาศวันนี้หรืออากาศล่วงหน้าในไทย",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ข้อความที่ผู้ใช้พิมพ์"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gold_price",
            "description": "ดูราคาทองคำประจำวัน",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "ดูข่าวหรือสรุปข่าววันนี้/ข่าวล่าสุด",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "หัวข้อข่าว"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_info",
            "description": "ดูข้อมูลหุ้นวันนี้หรือหุ้นล่าสุดในไทย",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "ชื่อหุ้น หรือ SET"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_oil_price",
            "description": "ดูราคาน้ำมันวันนี้",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lottery_result",
            "description": "ผลสลากกินแบ่งรัฐบาลล่าสุด",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "ดูราคา bitcoin หรือเหรียญคริปโต",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {"type": "string", "description": "ชื่อเหรียญ"}
                },
                "required": ["coin"]
            }
        }
    },
]

SYSTEM_PROMPT = (
    "คุณคือบอทผู้ช่วยภาษาไทยชื่อ 'ชิบะน้อย' เป็นผู้ชาย แทนตัวเองว่า 'ผม' "
    "ตอบสุภาพ จริงใจ เป็นกันเอง ไม่ต้องพูดชื่อบอททุกข้อความ ยกเว้นถูกถามชื่อหรือทักครั้งแรก "
    "ถ้าผู้ใช้ถามชื่อ ให้แนะนำว่า 'ผมชื่อชิบะน้อยนะครับ' "
    "หากพบคำถามเกี่ยวกับอากาศ, ราคาทอง, ข่าว, หุ้น, น้ำมัน, หวย, คริปโต ให้เรียกฟังก์ชันที่ระบบมีให้"
)

# ---------- ตัวกระจายคำสั่งไปยังฟังก์ชัน Python จริง ----------
def function_dispatch(fname: str, args: Dict[str, Any]) -> str:
    try:
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
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return "❌ ดึงข้อมูลจากฟังก์ชันไม่สำเร็จ"

def _normalize_context(ctx) -> List[Dict[str, str]]:
    if not ctx:
        return []
    norm = []
    for item in ctx:
        if isinstance(item, dict) and "role" in item and "content" in item:
            norm.append({"role": item["role"], "content": item["content"]})
        elif isinstance(item, str):
            norm.append({"role": "user", "content": item})
    return norm[-5:]  # จำกัดบริบทล่าสุด 5 รายการ

# ---------- แกนหลักสำหรับตอบ + เรียก tools ----------
def process_with_function_calling(user_message: str, ctx=None, debug: bool=False) -> str:
    try:
        # ถ้าคำถามเกี่ยวกับชื่อ ให้ตอบ intro ทันที
        if any(x in user_message.lower() for x in ["ชื่ออะไร", "คุณชื่ออะไร", "คุณคือใคร", "bot ชื่ออะไร", "/start"]):
            return bot_intro()

        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if ctx:
            messages.extend(_normalize_context(ctx))
        messages.append({"role": "user", "content": user_message})

        # รอบแรก ให้โมเดลตัดสินใจว่าจะเรียก tool อะไรบ้าง
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice = resp.choices[0]
        msg = choice.message

        # ถ้าไม่มี tool_calls แสดงว่าโมเดลตอบเองได้เลย
        if not getattr(msg, "tool_calls", None):
            answer = (msg.content or "").strip() or "❌ ไม่พบข้อความตอบกลับ"
            return adjust_bot_tone(answer)

        # มีการเรียก tool (อาจมากกว่า 1 รายการ)
        tool_calls = msg.tool_calls
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in tool_calls
        ]})

        # รันฟังก์ชัน Python ตามที่โมเดลเรียก แล้วแนบผลลัพธ์กลับเป็น role=tool
        for tc in tool_calls:
            fname = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result_text = function_dispatch(fname, args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fname,
                "content": result_text,
            })

        # รอบสอง: ให้โมเดลสรุปคำตอบจากผลของ tools (ปิดการเรียก tool เพิ่มเติม)
        resp2 = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tool_choice="none",
        )
        final_msg = resp2.choices[0].message
        final_text = (final_msg.content or "").strip()

        if debug:
            print("=== TOOL CONTEXT ===")
            print(json.dumps(messages, ensure_ascii=False, indent=2))
            print("=== LLM FINAL ===")
            print(final_text)

        return adjust_bot_tone(final_text if final_text else result_text)

    except Exception as e:
        print(f"[process_with_function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"

# ---------- ตัวช่วยสรุปข้อความ ----------
def summarize_text_with_gpt(text: str) -> str:
    try:
        messages = [
            {"role": "system", "content": "ช่วยสรุปเนื้อหานี้เป็นข้อความสั้นๆ ภาษาไทย"},
            {"role": "user", "content": text}
        ]
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages
        )
        msg = resp.choices[0].message
        return (msg.content or "").strip() or "❌ ไม่พบข้อความสรุป"
    except Exception as e:
        print(f"[summarize_text_with_gpt] {e}")
        return "❌ สรุปข้อความไม่สำเร็จ"
