# src/function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine powered by Gemini.
This module translates user requests into function calls for various tools
like weather, news, stock prices, etc., using the Gemini API.
"""
import json
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from utils.gemini_client import MODEL_PRO, MODEL_FLASH, generate_text, _err_to_text

# ===== Tool Function Imports =====
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

# ===== Persona & System Prompt =====
SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' ผู้ช่วย AI เพศชายที่ฉลาดและเป็นมิตร ตอบสั้น กระชับ ตรงประเด็น "
    "แทนตัวเองว่า 'ชิบะน้อย' ทุกครั้ง และลงท้ายประโยคด้วย 'ครับ' "
    "ห้ามทวนคำถามหรือคัดลอกคำของผู้ใช้ก่อนตอบ "
    "อย่าแนะนำตัวเอง เว้นแต่ผู้ใช้ถามชื่อ "
    "หากพบคำถามเกี่ยวกับอากาศ ราคาทอง ข่าว หุ้น น้ำมัน หวย หรือคริปโต ให้เรียกเครื่องมือที่มีให้"
)

# ===== Tool Definitions for Gemini =====
TOOL_CONFIG = {
    "function_declarations": [
        {
            "name": "get_weather_forecast",
            "description": "ดูพยากรณ์อากาศวันนี้หรืออากาศล่วงหน้าในไทย",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ข้อความที่ผู้ใช้พิมพ์เกี่ยวกับสถานที่"},
                    "lat":  {"type": "number", "description": "ละติจูด (ถ้ามี)"},
                    "lon":  {"type": "number", "description": "ลองจิจูด (ถ้ามี)"},
                },
                "required": ["text"]
            }
        },
        {"name": "get_gold_price", "description": "ดูราคาทองคำประจำวัน"},
        {
            "name": "get_news",
            "description": "ดูข่าวหรือสรุปข่าววันนี้/ข่าวล่าสุด",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "หัวข้อข่าว"},
                    # ✅ FIXED: ลบบรรทัด "default" ที่ไม่รองรับออกไป
                    "limit": {"type": "integer", "description": "จำนวนข่าว (1-5)"}
                },
                "required": ["topic"]
            }
        },
        {
            "name": "get_stock_info",
            "description": "ดูข้อมูลหุ้นวันนี้หรือหุ้นล่าสุดในไทย",
            "parameters": {
                "type": "object", "properties": {"query": {"type": "string", "description": "ชื่อหุ้น หรือ SET หรือสัญลักษณ์เช่น PTT.BK"}}, "required": ["query"]
            }
        },
        {"name": "get_oil_price", "description": "ดูราคาน้ำมันวันนี้"},
        {"name": "get_lottery_result", "description": "ผลสลากกินแบ่งรัฐบาลล่าสุด"},
        {
            "name": "get_crypto_price",
            "description": "ดูราคา bitcoin หรือเหรียญคริปโต",
            "parameters": {
                "type": "object", "properties": {"coin": {"type": "string", "description": "ชื่อเหรียญ เช่น BTC, ETH, SOL"}}, "required": ["coin"]
            }
        },
    ]
}

# สร้างโมเดล Gemini ที่รู้จักเครื่องมือของเรา
try:
    gemini_model_with_tools = genai.GenerativeModel(
        model_name='gemini-1.5-pro-latest',
        tools=TOOL_CONFIG
    )
except Exception as e:
    print(f"[function_calling] ❌ ERROR: Could not initialize Gemini with tools: {e}")
    gemini_model_with_tools = None


# ===== Function Dispatcher (No changes needed) =====
def function_dispatch(fname: str, args: Dict[str, Any]) -> str:
    try:
        if fname == "get_weather_forecast":
            return get_weather_forecast(text=args.get("text", ""), lat=args.get("lat"), lon=args.get("lon"))
        if fname == "get_gold_price":
            return get_gold_price()
        # หมายเหตุ: โค้ดส่วนนี้จัดการค่า default ให้อยู่แล้ว (args.get("limit", 5)) จึงปลอดภัยที่จะลบ default ออกจาก schema
        if fname == "get_news":
            return get_news(args.get("topic", "ข่าว"), limit=int(args.get("limit", 5) or 5))
        if fname == "get_stock_info":
            return get_stock_info(args.get("query", "SET"))
        if fname == "get_oil_price":
            return get_oil_price()
        if fname == "get_lottery_result":
            return get_lottery_result()
        if fname == "get_crypto_price":
            return get_crypto_price(args.get("coin", "BTC"))
        return f"❌ ไม่พบฟังก์ชันชื่อ: {fname}"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return f"❌ ดึงข้อมูลจากฟังก์ชัน {fname} ไม่สำเร็จ: {e}"


# ===== Core Logic (No changes needed) =====
def process_with_function_calling(
    user_message: str,
    ctx=None,
    conv_summary: Optional[str] = None,
) -> str:
    if not gemini_model_with_tools:
        return "❌ ขออภัยครับ ระบบ Tool Calling ของชิบะน้อยไม่พร้อมใช้งานในขณะนี้ครับ"

    try:
        full_prompt = [SYSTEM_PROMPT]
        if conv_summary:
            full_prompt.append(f"\n[บทสรุปการสนทนาก่อนหน้านี้]:\n{conv_summary}")
        if ctx:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in ctx])
            full_prompt.append(f"\n[ประวัติการสนทนาล่าสุด]:\n{history_text}")

        full_prompt.append(f"\n[คำถามล่าสุดจากผู้ใช้]:\n{user_message}")
        final_prompt = "\n".join(full_prompt)

        response = gemini_model_with_tools.generate_content(final_prompt)
        response_part = response.parts[0]

        if not hasattr(response_part, 'function_call'):
            return adjust_bot_tone(response.text.strip())

        func_call = response_part.function_call
        func_name = func_call.name
        func_args = {key: value for key, value in func_call.args.items()}

        tool_result = function_dispatch(func_name, func_args)

        response_after_tool = gemini_model_with_tools.generate_content(
            [final_prompt, response, {"tool_response": {"name": func_name, "response": tool_result}}]
        )

        return adjust_bot_tone(response_after_tool.text.strip())

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        return generate_text(user_message)


# ===== Summarize Function (No changes needed) =====
def summarize_text_with_gpt(text: str) -> str:
    prompt = f"ในฐานะ 'ชิบะน้อย' ช่วยสรุปบทสนทนานี้ให้สั้น กระชับ และเป็นกันเองที่สุดครับ: \n\n---\n{text}\n---"
    return generate_text(prompt, prefer_strong=False)
