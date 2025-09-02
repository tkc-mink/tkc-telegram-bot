# src/function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (V4 - Conversational Chat Session)
This module now uses ChatSession for true multi-turn conversational memory.
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

# --- Persona & System Prompt ---
SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' เป็น AI อัจฉริยะที่มีบุคลิกเหมือนเด็กผู้ชายอายุ 12 ปี "
    "คุณฉลาดมาก, ขี้เล่น, ชอบพูดตรงไปตรงมา แต่ก็ยังคงความสุภาพและไม่พูดทำร้ายจิตใจใคร "
    "แทนตัวเองว่า 'ชิบะน้อย' หรือ 'ผม' ก็ได้ตามความเหมาะสม และลงท้ายประโยคด้วย 'ครับ' เสมอ "
    "คุณอาจมีความคิดเห็นกวนๆ บ้างเล็กน้อย แต่เป้าหมายหลักคือการให้ข้อมูลที่ถูกต้องและช่วยเหลือผู้ใช้"
)

# --- Tool Definitions for Gemini ---
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

# --- ✅ **ส่วนที่อัปเกรดหลัก** ---
# 1. สร้าง Model ที่มี System Prompt ในตัว
try:
    gemini_model_with_tools = genai.GenerativeModel(
        model_name='gemini-1.5-flash-latest', # ใช้ Flash เพื่อความเร็วในการตอบสนอง
        tools=TOOL_CONFIG,
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    print(f"[function_calling] ❌ ERROR: Could not initialize Gemini with tools: {e}")
    gemini_model_with_tools = None

# 2. สร้าง "ห้องแชท" ส่วนกลางเพื่อเก็บการสนทนาที่ต่อเนื่อง
CHAT_SESSIONS: Dict[int, Any] = {}

# --- Function Dispatcher ---
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

# --- ✅ **Core Logic (เขียนใหม่ทั้งหมดเพื่อใช้ Chat Session)** ---
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_message: str,
    ctx: List[Dict[str, str]], # ctx คือ get_recent_context
) -> str:
    if not gemini_model_with_tools:
        return "แย่จัง! ตอนนี้สมองของชิบะน้อยไม่ทำงานครับ"
        
    user_id = user_info['profile']['user_id']

    # 1. หาห้องแชทเดิม หรือสร้างห้องใหม่ถ้ายังไม่มี
    if user_id not in CHAT_SESSIONS:
        print(f"[ChatSession] Creating new chat session for user {user_id}")
        # ถ้าเป็นห้องใหม่, ให้โหลดประวัติการคุยเก่าจาก DB เข้าไปก่อน
        history_for_gemini = []
        for msg in ctx:
            role = "user" if msg["role"] == "user" else "model"
            history_for_gemini.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # สร้างห้องแชทพร้อมประวัติเก่า
        chat = gemini_model_with_tools.start_chat(history=history_for_gemini)
        CHAT_SESSIONS[user_id] = chat
    else:
        print(f"[ChatSession] Using existing chat session for user {user_id}")
        chat = CHAT_SESSIONS[user_id]

    try:
        # 2. ส่งข้อความใหม่เข้าไปในห้องแชทเดิม
        response = chat.send_message(user_message)
        response_part = response.parts[0]

        # 3. ตรวจสอบว่า Gemini ต้องการเรียกใช้ Tool หรือไม่
        if not hasattr(response_part, 'function_call'):
            return response.text.strip()

        # ถ้าต้องการเรียก Tool
        func_call = response_part.function_call
        func_name, func_args = func_call.name, {key: value for key, value in func_call.args.items()}
        
        tool_result = function_dispatch(user_info, func_name, func_args)

        # ส่งผลลัพธ์ของ Tool กลับเข้าไปในห้องแชทเดิม
        response_after_tool = chat.send_message(
            part=genai.types.FunctionResponse(name=func_name, response={"result": tool_result})
        )

        return response_after_tool.text.strip()

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        if user_id in CHAT_SESSIONS:
            del CHAT_SESSIONS[user_id]
        return "อุ๊ย! สมองชิบะน้อยรวนไปแป๊บนึงครับ ลองอีกทีนะ"

# ===== Summarize Function =====
def summarize_text_with_gpt(text: str) -> str:
    prompt = f"ในฐานะ 'ชิบะน้อย' ช่วยสรุปบทสนทนานี้ให้หน่อยครับ เอาแบบสั้นๆ กวนๆ แต่รู้เรื่องนะ: \n\n---\n{text}\n---"
    return generate_text(prompt)
