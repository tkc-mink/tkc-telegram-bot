# src/function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine powered by Gemini.
This module translates user requests into function calls for various tools
like weather, news, stock prices, etc., using the Gemini API.
"""
import json
from typing import List, Dict, Any, Optional

# ===== NEW: Import Gemini Client and Tools =====
# เราจะเปลี่ยนมาเรียกใช้ Gemini Client ที่เราสร้างขึ้น
from utils.gemini_client import MODEL_PRO, MODEL_FLASH, generate_text, _err_to_text

# ===== Tool Function Imports (เหมือนเดิม) =====
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

# ===== Tool Definitions for Gemini =====
# Gemini ใช้การประกาศ Tool ที่แตกต่างออกไปเล็กน้อย แต่หลักการเหมือนเดิม
# เราจะใช้ MODEL_PRO สำหรับ Tool Calling เพราะมีความสามารถสูงสุด
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
                    "limit": {"type": "integer", "description": "จำนวนข่าว (1-5)", "default": 3}
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


# ===== Function Dispatcher (เหมือนเดิม) =====
def function_dispatch(fname: str, args: Dict[str, Any]) -> str:
    # ... (เนื้อหาฟังก์ชันนี้เหมือนเดิมทุกประการ ไม่ต้องแก้ไข) ...
    try:
        if fname == "get_weather_forecast":
            return get_weather_forecast(text=args.get("text", ""), lat=args.get("lat"), lon=args.get("lon"))
        if fname == "get_gold_price":
            return get_gold_price()
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


# ===== Core Logic (Refactored for Gemini) =====
def process_with_function_calling(
    user_message: str,
    ctx=None, # Context จะถูกรวมเข้าไปใน prompt โดยตรง
    conv_summary: Optional[str] = None,
) -> str:
    """
    ตอบด้วย Gemini + tools โดยสร้าง prompt ที่มีบริบทและสรุปบทสนทนา
    """
    if not gemini_model_with_tools:
        return "❌ ขออภัยค่ะ ระบบ Tool Calling ของ Gemini ไม่พร้อมใช้งานในขณะนี้"

    try:
        # 1. สร้าง Prompt ที่สมบูรณ์สำหรับ Gemini
        full_prompt = []
        full_prompt.append(
            "คุณเป็นผู้ช่วย AI ภาษาไทยที่เป็นมิตรและตอบตรงประเด็น "
            "หากจำเป็น ให้ใช้เครื่องมือ (functions) ที่มีเพื่อหาคำตอบที่ถูกต้องที่สุด"
        )
        if conv_summary:
            full_prompt.append(f"\n[บทสรุปการสนทนาก่อนหน้านี้]:\n{conv_summary}")
        if ctx:
            # รวม context เข้าไปใน prompt (ประวัติการแชทล่าสุด)
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in ctx])
            full_prompt.append(f"\n[ประวัติการสนทนาล่าสุด]:\n{history_text}")
        
        full_prompt.append(f"\n[คำถามล่าสุดจากผู้ใช้]:\n{user_message}")
        
        final_prompt = "\n".join(full_prompt)

        # 2. เรียก Gemini (รอบแรก) เพื่อดูว่าต้องใช้ Tool หรือไม่
        response = gemini_model_with_tools.generate_content(final_prompt)
        response_part = response.parts[0]

        # 3. ถ้า Gemini ไม่เรียกใช้ Tool ก็ตอบกลับได้เลย
        if not hasattr(response_part, 'function_call'):
            return response.text.strip()

        # 4. ถ้า Gemini เรียกใช้ Tool
        # Gemini อาจเรียกใช้หลาย tool พร้อมกันได้ในอนาคต (ตอนนี้รองรับทีละ 1)
        func_call = response_part.function_call
        func_name = func_call.name
        func_args = {key: value for key, value in func_call.args.items()}
        
        # 5. เรียกใช้ฟังก์ชันในโค้ดของเรา
        tool_result = function_dispatch(func_name, func_args)

        # 6. ส่งผลลัพธ์ของ Tool กลับไปให้ Gemini เพื่อสร้างคำตอบสุดท้าย
        response_after_tool = gemini_model_with_tools.generate_content(
            [
                final_prompt, # Prompt เดิม
                response,     # การตัดสินใจของ Gemini ในรอบแรก
                { # ผลลัพธ์จาก Tool
                    "tool_response": {
                        "name": func_name,
                        "response": tool_result,
                    }
                }
            ]
        )
        
        return response_after_tool.text.strip()

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        # หากระบบ Tool ขัดข้อง ให้ใช้ระบบตอบคำถามธรรมดาแทน
        return generate_text(user_message)


# ===== Summarize Function (Refactored for Gemini) =====
def summarize_text_with_gpt(text: str) -> str:
    """สรุปข้อความด้วย Gemini (เปลี่ยนชื่อจากเดิมเพื่อความชัดเจน)"""
    prompt = f"ช่วยสรุปบทสนทนานี้ให้สั้น กระชับ และเป็นกันเองที่สุด: \n\n---\n{text}\n---"
    return generate_text(prompt, prefer_strong=False)
