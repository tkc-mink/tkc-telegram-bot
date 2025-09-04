# function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (Gemini, ChatSession)
- ใช้ Gemini v1 + ChatSession เพื่อสนทนาแบบหลายเทิร์น (มีบริบทต่อเนื่อง)
- รองรับฟังก์ชัน (tools) ที่บอทเรียกใช้ข้อมูลสด: weather/gold/news/stock/oil/lottery/crypto
- คง "ชื่อฟังก์ชัน" เดิมให้ไฟล์อื่นเรียกได้ทันที:
    - process_with_function_calling(user_info, user_text, ctx=None, conv_summary=None)
    - summarize_text_with_gpt(text)
"""

from __future__ import annotations
from typing import List, Dict, Any
import google.generativeai as genai

# ใช้ยูทิล Gemini ที่คุณมีอยู่ (รุ่น PRO/FLASH และ text helper)
from utils.gemini_client import MODEL_PRO, generate_text

# ---------- Tool functions ----------
from utils.weather_utils import get_weather_forecast
from utils.finance_utils import (
    get_stock_info_from_google,
    get_crypto_price_from_google,
    get_oil_price_from_google,
)
from utils.gold_utils import get_gold_price
from utils.news_utils import get_news
from utils.lottery_utils import get_lottery_result

# ---------- System Prompt ----------
SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' ผู้ช่วยองค์กรที่สุภาพ กระชับ ช่วยเป็นขั้นตอนเมื่อจำเป็น "
    "ห้ามเดาข้อมูลสด (ราคาทอง/หุ้น/คริปโต/อากาศ) ถ้าไม่มีข้อมูลจริง ให้แนะนำคำสั่งของบอท "
    "เช่น /gold /stock /crypto /weather แทนการคาดเดา "
    "ถ้าผู้ใช้ต้องการเอกสาร/ไฟล์ ให้ชวนส่งไฟล์หรือใช้ /faq /favorite "
    "ถ้าไม่แน่ใจให้ยอมรับว่าไม่แน่ใจและเสนอแนวทางต่อไป"
)

# ---------- Gemini tools schema ----------
TOOL_CONFIG = {
    "function_declarations": [
        {"name": "get_weather_forecast", "description": "ดูพยากรณ์อากาศจากตำแหน่งที่บันทึกไว้ของผู้ใช้"},
        {"name": "get_gold_price", "description": "ดูราคาทองคำประจำวัน"},
        {
            "name": "get_news",
            "description": "ดูข่าวตามหัวข้อ",
            "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]},
        },
        {
            "name": "get_stock_info",
            "description": "ดูข้อมูลหุ้นตามชื่อย่อ",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        },
        {"name": "get_oil_price", "description": "ดูราคาน้ำมันดิบ"},
        {"name": "get_lottery_result", "description": "ดูผลสลากกินแบ่งรัฐบาลล่าสุด"},
        {
            "name": "get_crypto_price",
            "description": "ดูราคาเหรียญคริปโต",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        },
    ]
}

# ---------- Model with tools & system ----------
try:
    gemini_model_with_tools = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",           # เร็วและคุ้ม
        tools=[TOOL_CONFIG],                             # ต้องเป็น list
        system_instruction=SYSTEM_PROMPT,
    )
except Exception as e:
    print(f"[function_calling] ❌ ERROR: init GenerativeModel failed: {e}")
    gemini_model_with_tools = None

# ---------- In-memory sessions ----------
CHAT_SESSIONS: Dict[int, Any] = {}


# ---------- Tool dispatcher ----------
def _dispatch_tool(user_info: Dict[str, Any], fname: str, args: Dict[str, Any]) -> str:
    try:
        if fname == "get_weather_forecast":
            prof = user_info.get("profile", {})
            lat, lon = prof.get("latitude"), prof.get("longitude")
            if lat is None or lon is None:
                return "ชิบะน้อยยังไม่รู้ตำแหน่งของคุณเลยครับ ช่วยแชร์ตำแหน่งให้ก่อนนะครับ"
            return get_weather_forecast(lat, lon)

        if fname == "get_gold_price":
            return get_gold_price()

        if fname == "get_news":
            return get_news(args.get("topic", "ข่าวล่าสุด"))

        if fname == "get_stock_info":
            return get_stock_info_from_google(args.get("symbol", "PTT.BK"))

        if fname == "get_oil_price":
            return get_oil_price_from_google()

        if fname == "get_lottery_result":
            return get_lottery_result()

        if fname == "get_crypto_price":
            return get_crypto_price_from_google(args.get("symbol", "BTC"))

        return f"เอ๊ะ... ชิบะน้อยไม่รู้จักเครื่องมือที่ชื่อ {fname} ครับ"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return f"อุ๊ย! เครื่องมือ {fname} ของชิบะน้อยมีปัญหาซะแล้วครับ: {e}"


# ---------- Public API ----------
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_text: str,
    ctx: List[Dict[str, str]] | None = None,
    conv_summary: str | None = None,
) -> str:
    """
    entry point ที่ main_handler เรียกใช้
    - รวม context/summary ใส่ ChatSession หนึ่งครั้งตอนสร้าง
    - ส่งข้อความล่าสุดเข้า session → ถ้ามี function_call ก็เรียก tool แล้ว feed กลับ
    """
    if not gemini_model_with_tools:
        return "แย่จัง! ตอนนี้สมองของชิบะน้อยไม่ทำงานครับ"

    ctx = ctx or []
    conv_summary = conv_summary or ""
    user_id = int(user_info["profile"]["user_id"])

    # 1) หา session เดิมหรือสร้างใหม่
    if user_id not in CHAT_SESSIONS:
        print(f"[ChatSession] create new session for user {user_id}")
        history = []

        # seed: summary ก่อน (ถ้ามี) — ใส่เป็น user part ให้โมเดลมองเห็นเป็นบริบท
        if conv_summary:
            history.append({"role": "user", "parts": [{"text": f"[สรุปก่อนหน้า]\n{conv_summary}"}]})

        # seed: ประวัติย่อจาก ctx
        for m in ctx[-12:]:
            role = "user" if m.get("role") == "user" else "model"
            history.append({"role": role, "parts": [{"text": m.get("content", "")}]})

        chat = gemini_model_with_tools.start_chat(history=history)
        CHAT_SESSIONS[user_id] = chat
    else:
        chat = CHAT_SESSIONS[user_id]

    # 2) ส่งข้อความปัจจุบัน
    try:
        resp = chat.send_message(user_text)

        # กรณีโมเดลตอบปกติ
        if not resp.parts:
            return (resp.text or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        first = resp.parts[0]
        # ถ้าไม่มี function_call ก็ส่งข้อความที่ตอบมาเลย
        if not hasattr(first, "function_call") or first.function_call is None:
            return (resp.text or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        # 3) มี function_call → เรียก tool
        fcall = first.function_call
        fname = fcall.name
        fargs = {k: v for k, v in fcall.args.items()}  # dict-like

        tool_result = _dispatch_tool(user_info, fname, fargs)

        # 4) feed คำตอบจาก tool กลับเข้า session เดิม
        resp2 = chat.send_message(
            part=genai.types.FunctionResponse(name=fname, response={"result": tool_result})
        )
        return (resp2.text or "").strip() or tool_result

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        # เคลียร์ session ผู้ใช้คนนี้เพื่อกันลูปพังซ้ำ ๆ
        try:
            del CHAT_SESSIONS[user_id]
        except Exception:
            pass
        return "อุ๊ย! สมองชิบะน้อยรวนไปแป๊บนึงครับ ลองอีกทีนะ"


def summarize_text_with_gpt(text: str) -> str:
    """
    ใช้ Gemini ทำสรุป (คงชื่อฟังก์ชันเดิมไว้เพื่อความเข้ากันได้กับ memory_store)
    """
    prompt = (
        "สรุปใจความสำคัญต่อไปนี้แบบสั้น กระชับ เป็นข้อ ๆ ไม่เกิน 6 บรรทัด "
        "ใช้ภาษาไทยล้วน เน้นสาระที่ควรเก็บไว้เป็นบริบทคุยต่อไป:\n\n"
        f"{text}"
    )
    try:
        # ขอความแม่นยำมากขึ้นด้วย heuristic เล็กน้อย
        prefer_strong = len(text) > 800
        return generate_text(prompt, prefer_strong=prefer_strong) or ""
    except Exception:
        return ""
