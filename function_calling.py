# src/function_calling.py
# -*- coding: utf-8 -*-

import os
import json
from typing import List, Dict, Any, Optional

# ใช้ client และตัวเลือกโมเดลเดียวกับทั้งระบบ
from utils.openai_client import client, DEFAULT_MODEL, STRONG_MODEL, pick_model
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


# ---------- Tools (Function Calling) ----------
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
        if fname == "get_gold_price":
            return get_gold_price()
        if fname == "get_news":
            return get_news(args.get("topic", "ข่าว"))
        if fname == "get_stock_info":
            return get_stock_info(args.get("query", "หุ้น"))
        if fname == "get_oil_price":
            return get_oil_price()
        if fname == "get_lottery_result":
            return get_lottery_result()
        if fname == "get_crypto_price":
            return get_crypto_price(args.get("coin", "bitcoin"))
        return "❌ ฟังก์ชันนี้ยังไม่รองรับในระบบ"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return "❌ ดึงข้อมูลจากฟังก์ชันไม่สำเร็จ"


def _normalize_context(ctx) -> List[Dict[str, str]]:
    if not ctx:
        return []
    norm: List[Dict[str, str]] = []
    for item in ctx:
        if isinstance(item, dict) and "role" in item and "content" in item:
            norm.append({"role": item["role"], "content": item["content"]})
        elif isinstance(item, str):
            norm.append({"role": "user", "content": item})
    return norm[-5:]  # จำกัดบริบทล่าสุด 5 รายการ


# ---------- แกนหลักสำหรับตอบ + เรียก tools ----------
def process_with_function_calling(
    user_message: str,
    ctx=None,
    debug: bool = False,
) -> str:
    """
    กลไกหลักสำหรับตอบกลับด้วย LLM + ฟังก์ชันจริง
    - ปกติใช้โมเดล DEFAULT_MODEL (gpt-5-mini)
    - ถ้าข้อความยาก/ยาว/มีโค้ด หรือผู้ใช้สั่ง 'ใช้ gpt5' หรือ '/gpt5 ...' จะยกไป STRONG_MODEL (gpt-5)
    - มี fallback สลับโมเดลอัตโนมัติเมื่อเรียกล้มเหลว
    """
    try:
        text = user_message or ""
        low = text.lower()

        # ชื่อ/เริ่มต้นบทสนทนา
        if any(k in low for k in ["ชื่ออะไร", "คุณชื่ออะไร", "คุณคือใคร", "bot ชื่ออะไร", "/start"]):
            return bot_intro()

        # คำสั่งบังคับให้ใช้ gpt-5
        force_model: Optional[str] = None
        if low.startswith("/gpt5 "):
            force_model = STRONG_MODEL
            text = text.split(" ", 1)[1]  # ตัด prefix ออกก่อนส่งให้โมเดล
        elif "ใช้ gpt5" in low or "use gpt5" in low:
            force_model = STRONG_MODEL

        # เตรียม messages
        messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if ctx:
            messages.extend(_normalize_context(ctx))
        messages.append({"role": "user", "content": text})

        # เลือกโมเดล (อัตโนมัติหรือบังคับ)
        model = force_model or pick_model(text)

        # รอบแรก ให้โมเดลตัดสินใจว่าจะเรียก tools หรือไม่
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
        except Exception as e1:
            # fallback: ลองอีกโมเดล
            alt = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
            resp = client.chat.completions.create(
                model=alt,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            model = alt  # ใช้ตัวที่สำเร็จ

        msg = resp.choices[0].message

        # ถ้าไม่มี tool_calls โมเดลตอบเองได้เลย
        if not getattr(msg, "tool_calls", None):
            answer = (msg.content or "").strip() or "❌ ไม่พบข้อความตอบกลับ"
            return adjust_bot_tone(answer)

        # มีการเรียก tool (อาจมากกว่า 1)
        tool_calls = msg.tool_calls or []
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        # รันฟังก์ชัน Python ตามที่โมเดลเรียก แล้วแนบผลลัพธ์กลับเป็น role=tool
        last_result_text: Optional[str] = None
        for tc in tool_calls:
            fname = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result_text = function_dispatch(fname, args)
            last_result_text = result_text
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fname,
                "content": result_text,
            })

        # รอบสอง: ให้โมเดลสรุปคำตอบจากผลของ tools (ปิด tools เพิ่มเติม)
        try:
            resp2 = client.chat.completions.create(
                model=model,
                messages=messages,
                tool_choice="none",
            )
        except Exception:
            alt = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
            resp2 = client.chat.completions.create(
                model=alt,
                messages=messages,
                tool_choice="none",
            )

        final_msg = resp2.choices[0].message
        final_text = (final_msg.content or "").strip()

        if debug:
            try:
                print("=== TOOL CONTEXT ===")
                print(json.dumps(messages, ensure_ascii=False, indent=2))
                print("=== LLM FINAL ===")
                print(final_text)
            except Exception:
                pass

        return adjust_bot_tone(final_text if final_text else (last_result_text or ""))

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
            model=DEFAULT_MODEL,
            messages=messages
        )
        msg = resp.choices[0].message
        return (msg.content or "").strip() or "❌ ไม่พบข้อความสรุป"
    except Exception as e:
        print(f"[summarize_text_with_gpt] {e}")
        return "❌ สรุปข้อความไม่สำเร็จ"
