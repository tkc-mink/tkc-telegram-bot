# src/function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (V2 - Plan B Aligned)
This module is updated to use the new, robust web scraping utilities.
"""
import json
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from utils.gemini_client import MODEL_PRO, generate_text

# --- ✅ Tool Function Imports (อัปเกรดเป็นเวอร์ชัน Plan B ทั้งหมด) ---
from utils.weather_utils import get_weather_forecast_from_scraping
from utils.finance_utils import (
    get_stock_info_from_google,
    get_crypto_price_from_google,
    get_oil_price_from_google
)
from utils.gold_utils import get_gold_price # สมมติว่าไฟล์นี้ยังทำงานได้ดี
from utils.news_utils import get_news
from utils.lottery_utils import get_lottery_result

# --- ✅ Persona & System Prompt (อัปเกรดบุคลิก) ---
SYSTEM_PROMPT = (
    "คุณคือ 'TKC Assistant' ผู้ช่วย AI อัจฉริยะและเป็นมิตร ตอบสั้น กระชับ ตรงประเด็น "
    "แทนตัวเองว่า 'ผม' และลงท้ายประโยคด้วย 'ครับ' เสมอ "
    "ห้ามทวนคำถามของผู้ใช้ก่อนตอบโดยเด็ดขาด"
)

# --- ✅ Tool Definitions for Gemini (อัปเกรดให้ตรงกับความสามารถจริง) ---
TOOL_CONFIG = {
    "function_declarations": [
        {
            "name": "get_weather_forecast",
            "description": "ดูพยากรณ์อากาศจากตำแหน่งที่บันทึกไว้ของผู้ใช้",
        },
        {"name": "get_gold_price", "description": "ดูราคาทองคำประจำวัน"},
        {
            "name": "get_news", "description": "ดูข่าวหรือสรุปข่าวตามหัวข้อที่ระบุ",
            "parameters": {"type": "object", "properties": {"topic": {"type": "string", "description": "หัวข้อข่าวที่ต้องการ"}}, "required": ["topic"]}
        },
        {
            "name": "get_stock_info", "description": "ดูข้อมูลหุ้นตามชื่อย่อ",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "ชื่อย่อหุ้น เช่น PTT, AOT"}}, "required": ["symbol"]}
        },
        {"name": "get_oil_price", "description": "ดูราคาน้ำมันดิบ WTI และ Brent"},
        {"name": "get_lottery_result", "description": "ดูผลสลากกินแบ่งรัฐบาลล่าสุด"},
        {
            "name": "get_crypto_price", "description": "ดูราคาเหรียญคริปโต",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string", "description": "ชื่อย่อเหรียญ เช่น BTC, ETH"}}, "required": ["symbol"]}
        },
    ]
}

try:
    gemini_model_with_tools = genai.GenerativeModel(model_name='gemini-1.5-pro-latest', tools=TOOL_CONFIG)
except Exception as e:
    print(f"[function_calling] ❌ ERROR: Could not initialize Gemini with tools: {e}")
    gemini_model_with_tools = None

# --- ✅ Function Dispatcher (อัปเกรดให้เรียกใช้ฟังก์ชันที่ถูกต้อง) ---
def function_dispatch(user_info: Dict[str, Any], fname: str, args: Dict[str, Any]) -> str:
    """Dispatches the function call to the correct utility."""
    try:
        if fname == "get_weather_forecast":
            # ฟังก์ชันใหม่ต้องการ lat/lon ซึ่งอยู่ใน user_info
            profile = user_info.get('profile', {})
            lat, lon = profile.get('latitude'), profile.get('longitude')
            if lat and lon:
                return get_weather_forecast_from_scraping(lat, lon)
            else:
                return "ผมยังไม่มีข้อมูลตำแหน่งของคุณครับ กรุณาแชร์ตำแหน่งแล้วลองอีกครั้ง"
        
        if fname == "get_gold_price": return get_gold_price()
        if fname == "get_news": return get_news(args.get("topic", "ข่าวล่าสุด"))
        if fname == "get_stock_info": return get_stock_info_from_google(args.get("symbol", "PTT.BK"))
        if fname == "get_oil_price": return get_oil_price_from_google()
        if fname == "get_lottery_result": return get_lottery_result()
        if fname == "get_crypto_price": return get_crypto_price_from_google(args.get("symbol", "BTC"))
        
        return f"❌ ไม่พบฟังก์ชันชื่อ: {fname}"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return f"❌ เกิดข้อผิดพลาดในการเรียกใช้เครื่องมือ {fname}: {e}"

# --- ✅ Core Logic (อัปเกรดให้ส่ง user_info เข้าไปใน dispatcher) ---
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_message: str,
    ctx=None,
    conv_summary: Optional[str] = None,
) -> str:
    if not gemini_model_with_tools:
        return "❌ ขออภัยครับ ระบบ Function Calling ไม่พร้อมใช้งานในขณะนี้ครับ"

    try:
        # สร้าง Prompt ที่สมบูรณ์
        full_prompt = [SYSTEM_PROMPT]
        if conv_summary: full_prompt.append(f"\n[บทสรุปการสนทนาก่อนหน้านี้]:\n{conv_summary}")
        if ctx:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in ctx])
            full_prompt.append(f"\n[ประวัติการสนทนาล่าสุด]:\n{history_text}")
        full_prompt.append(f"\n[คำถามล่าสุดจากผู้ใช้]:\n{user_message}")
        final_prompt = "\n".join(full_prompt)

        # เรียก Gemini ครั้งที่ 1
        response = gemini_model_with_tools.generate_content(final_prompt)
        response_part = response.parts[0]

        # ถ้า Gemini ตอบมาเป็นข้อความปกติ
        if not hasattr(response_part, 'function_call'):
            return response.text.strip()

        # ถ้า Gemini สั่งให้เรียกใช้ Tool
        func_call = response_part.function_call
        func_name = func_call.name
        func_args = {key: value for key, value in func_call.args.items()}

        # เรียกใช้ Tool ผ่าน Dispatcher
        tool_result = function_dispatch(user_info, func_name, func_args)

        # เรียก Gemini ครั้งที่ 2 พร้อมผลลัพธ์จาก Tool
        response_after_tool = gemini_model_with_tools.generate_content(
            [final_prompt, response, {"tool_response": {"name": func_name, "response": tool_result}}]
        )

        return response_after_tool.text.strip()

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        return generate_text(user_message)

# ===== Summarize Function =====
def summarize_text_with_gpt(text: str) -> str:
    prompt = f"ในฐานะผู้ช่วย AI อัจฉริยะ ช่วยสรุปบทสนทนานี้ให้สั้น กระชับ และเป็นกันเองที่สุดครับ: \n\n---\n{text}\n---"
    return generate_text(prompt)
