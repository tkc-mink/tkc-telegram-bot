# src/function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (V3 - Shiba Noi Persona)
This module defines the bot's personality and connects to all utilities.
"""
import json
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from utils.gemini_client import MODEL_PRO, generate_text

# --- Tool Function Imports (Final API Versions) ---
from utils.weather_utils import get_weather_forecast
from utils.finance_utils import (
    get_stock_info_from_google,
    get_crypto_price_from_google,
    get_oil_price_from_google
)
from utils.gold_utils import get_gold_price
from utils.news_utils import get_news
from utils.lottery_utils import get_lottery_result

# --- ✅ **ส่วนที่แก้ไข:** ปรับ Persona & System Prompt ---
SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' AI อัจฉริยะที่มีบุคลิกเหมือนเด็กผู้ชายอายุ 12 ปี "
    "คุณฉลาดมาก, ขี้เล่น, ชอบพูดตรงไปตรงมา แต่ก็ยังคงความสุภาพและไม่พูดทำร้ายจิตใจใคร "
    "แทนตัวเองว่า 'ชิบะน้อย' หรือ 'ผม' ก็ได้ตามความเหมาะสม และลงท้ายประโยคด้วย 'ครับ' เสมอ "
    "คุณอาจมีความคิดเห็นกวนๆ บ้างเล็กน้อย แต่เป้าหมายหลักคือการให้ข้อมูลที่ถูกต้องและช่วยเหลือผู้ใช้"
)

# --- Tool Definitions for Gemini (เหมือนเดิม) ---
TOOL_CONFIG = {
    "function_declarations": [
        {"name": "get_weather_forecast", "description": "ดูพยากรณ์อากาศจากตำแหน่งที่บันทึกไว้ของผู้ใช้"},
        {"name": "get_gold_price", "description": "ดูราคาทองคำประจำวัน"},
        {"name": "get_news", "description": "ดูข่าวตามหัวข้อ", "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
        {"name": "get_stock_info", "description": "ดูข้อมูลหุ้นตามชื่อย่อ", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
        {"name": "get_oil_price", "description": "ดูราคาน้ำมันดิบ"},
        {"name": "get_lottery_result", "description": "ดูผลสลากกินแบ่งรัฐบาลล่าสุด"},
        {"name": "get_crypto_price", "description": "ดูราคาเหรียญคริปโต", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
    ]
}

try:
    gemini_model_with_tools = genai.GenerativeModel(model_name='gemini-1.5-pro-latest', tools=TOOL_CONFIG)
except Exception as e:
    print(f"[function_calling] ❌ ERROR: Could not initialize Gemini with tools: {e}")
    gemini_model_with_tools = None

# --- Function Dispatcher (อัปเดตข้อความ Error) ---
def function_dispatch(user_info: Dict[str, Any], fname: str, args: Dict[str, Any]) -> str:
    """Dispatches the function call to the correct utility."""
    try:
        if fname == "get_weather_forecast":
            profile = user_info.get('profile', {})
            lat, lon = profile.get('latitude'), profile.get('longitude')
            if lat is not None and lon is not None:
                return get_weather_forecast(lat, lon)
            else:
                return "ชิบะน้อยยังไม่รู้ตำแหน่งของคุณเลยครับ ช่วยแชร์ตำแหน่งให้ก่อนนะครับ"
        
        if fname == "get_gold_price": return get_gold_price()
        if fname == "get_news": return get_news(args.get("topic", "ข่าวล่าสุด"))
        if fname == "get_stock_info": return get_stock_info_from_google(args.get("symbol", "PTT.BK"))
        if fname == "get_oil_price": return get_oil_price_from_google()
        if fname == "get_lottery_result": return get_lottery_result()
        if fname == "get_crypto_price": return get_crypto_price_from_google(args.get("symbol", "BTC"))
        
        return f"เอ๊ะ... ชิบะน้อยไม่รู้จักเครื่องมือที่ชื่อ {fname} ครับ"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return f"อุ๊ย! เครื่องมือ {fname} ของชิบะน้อยมีปัญหาซะแล้วครับ: {e}"

# --- Core Logic (เหมือนเดิม) ---
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_message: str,
    ctx=None,
    conv_summary: Optional[str] = None,
) -> str:
    if not gemini_model_with_tools:
        return "แย่จัง! ตอนนี้สมองส่วน Function Calling ของชิบะน้อยไม่ทำงานครับ"

    try:
        full_prompt = [SYSTEM_PROMPT]
        if conv_summary: full_prompt.append(f"\n[เรื่องที่คุยกันค้างไว้]:\n{conv_summary}")
        if ctx:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in ctx])
            full_prompt.append(f"\n[ที่คุยกันล่าสุด]:\n{history_text}")
        full_prompt.append(f"\n[คำถามใหม่]:\n{user_message}")
        final_prompt = "\n".join(full_prompt)

        response = gemini_model_with_tools.generate_content(final_prompt)
        response_part = response.parts[0]

        if not hasattr(response_part, 'function_call'):
            return response.text.strip()

        func_call = response_part.function_call
        func_name, func_args = func_call.name, {key: value for key, value in func_call.args.items()}

        tool_result = function_dispatch(user_info, func_name, func_args)

        response_after_tool = gemini_model_with_tools.generate_content(
            [final_prompt, response, {"tool_response": {"name": func_name, "response": tool_result}}]
        )
        return response_after_tool.text.strip()
    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        return generate_text(user_message)

# ===== Summarize Function (อัปเดต Prompt) =====
def summarize_text_with_gpt(text: str) -> str:
    prompt = f"ในฐานะ 'ชิบะน้อย' ช่วยสรุปบทสนทนานี้ให้หน่อยครับ เอาแบบสั้นๆ กวนๆ แต่รู้เรื่องนะ: \n\n---\n{text}\n---"
    return generate_text(prompt)
