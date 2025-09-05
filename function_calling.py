# function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (Gemini, ChatSession)
- สนทนาแบบหลายเทิร์น (มีบริบทต่อเนื่อง) ด้วย Gemini v1
- รองรับเครื่องมือเรียกข้อมูลสด: weather/gold/news/stock/oil/lottery/crypto
- API:
    process_with_function_calling(user_info, user_text, ctx=None, conv_summary=None)
    summarize_text_with_gpt(text)
"""
from __future__ import annotations
from typing import List, Dict, Any
import os
import time
from threading import RLock

import google.generativeai as genai

# ใช้เฉพาะฟังก์ชันที่ต้องใช้จริง เพื่อกัน ImportError
from utils.gemini_client import generate_text

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
    # SDK 0.8.x ใช้พารามิเตอร์ชื่อ "model"
    gemini_model_with_tools = genai.GenerativeModel(
        model="gemini-1.5-flash-latest",
        tools=[TOOL_CONFIG],  # list ของ tool blocks
        system_instruction=SYSTEM_PROMPT,
    )
except Exception as e:
    print(f"[function_calling] ❌ ERROR: init GenerativeModel failed: {e}")
    gemini_model_with_tools = None

# ---------- In-memory sessions (LRU + lock) ----------
CHAT_SESSIONS: Dict[int, Any] = {}
_LAST_USED: Dict[int, float] = {}
_SESS_LOCK = RLock()
SESSION_CAP = int(os.getenv("CHAT_SESSION_CAP", "200"))  # จำกัดจำนวน session ในหน่วยความจำ

# ---------- Tool output guard ----------
MAX_TOOL_RESULT_CHARS = int(os.getenv("MAX_TOOL_RESULT_CHARS", "4000"))  # กันผลลัพธ์ยาวเกิน

def _clip(s: str, n: int = MAX_TOOL_RESULT_CHARS) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else (s[: n - 200].rstrip() + "\n…(ตัดเพื่อความกระชับ)")

# ---------- Tool dispatcher ----------
def _dispatch_tool(user_info: Dict[str, Any], fname: str, args: Dict[str, Any]) -> str:
    try:
        if fname == "get_weather_forecast":
            prof = user_info.get("profile", {}) or {}
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

# ---------- Helpers ----------
def _ensure_session(user_id: int, ctx: List[Dict[str, str]], conv_summary: str) -> Any:
    with _SESS_LOCK:
        chat = CHAT_SESSIONS.get(user_id)
        if chat is not None:
            _LAST_USED[user_id] = time.time()
            return chat

        print(f"[ChatSession] create new session for user {user_id}")
        history = []
        if conv_summary:
            history.append({"role": "user", "parts": [{"text": f"[สรุปก่อนหน้า]\n{conv_summary}"}]})
        for m in (ctx or [])[-12:]:
            role = "user" if (m.get("role") == "user") else "model"
            history.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        chat = gemini_model_with_tools.start_chat(history=history)
        CHAT_SESSIONS[user_id] = chat
        _LAST_USED[user_id] = time.time()

        # LRU eviction
        if len(CHAT_SESSIONS) > max(SESSION_CAP, 1):
            oldest_uid = min(_LAST_USED, key=_LAST_USED.get)
            if oldest_uid != user_id:
                try:
                    del CHAT_SESSIONS[oldest_uid]
                    del _LAST_USED[oldest_uid]
                    print(f"[ChatSession] evict user {oldest_uid}")
                except Exception:
                    pass
        return chat

def _clear_session(user_id: int) -> None:
    with _SESS_LOCK:
        if user_id in CHAT_SESSIONS:
            del CHAT_SESSIONS[user_id]
        if user_id in _LAST_USED:
            del _LAST_USED[user_id]

def _send_function_response(chat: Any, name: str, tool_result: str):
    """
    ส่ง FunctionResponse ให้ครอบคลุมหลายเวอร์ชัน SDK:
    - ลองใช้ genai.types.FunctionResponse ก่อน
    - ถ้าไม่สำเร็จ ตกลงมาใช้ dict {"function_response": {...}}
    """
    try:
        payload = genai.types.FunctionResponse(name=name, response={"result": tool_result})
        return chat.send_message(part=payload)
    except Exception:
        return chat.send_message({"function_response": {"name": name, "response": {"result": tool_result}}})

# ---------- Public API ----------
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_text: str,
    ctx: List[Dict[str, str]] | None = None,
    conv_summary: str | None = None,
) -> str:
    if not gemini_model_with_tools:
        return "แย่จัง! ตอนนี้สมองของชิบะน้อยไม่ทำงานครับ"

    ctx = ctx or []
    conv_summary = conv_summary or ""
    try:
        user_id = int(user_info["profile"]["user_id"])
    except Exception:
        return "ชิบะน้อยงง user_id นิดหน่อยครับ ลองใหม่อีกทีนะ"

    # /reset → ล้างบริบทของผู้ใช้
    if user_text.strip().lower() in {"/reset", "รีเซ็ต", "เริ่มใหม่"}:
        _clear_session(user_id)
        return "โอเค! เคลียร์บริบทให้แล้วครับ เริ่มคุยใหม่ได้เลย"

    chat = _ensure_session(user_id, ctx, conv_summary)

    try:
        # 1) ส่งข้อความปัจจุบัน
        resp = chat.send_message(user_text)

        # ถ้าไม่มี parts เลย ให้ส่งข้อความธรรมดา
        if not getattr(resp, "parts", None):
            return (getattr(resp, "text", "") or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        # 2) หา function_call ถ้ามี
        fpart = next((p for p in resp.parts if getattr(p, "function_call", None)), None)
        if fpart is None:
            return (resp.text or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        fcall = fpart.function_call
        fname = getattr(fcall, "name", "")
        raw_args = getattr(fcall, "args", None)

        # รองรับ args หลายรูปแบบ
        if hasattr(raw_args, "items"):
            fargs = {k: v for k, v in raw_args.items()}
        elif isinstance(raw_args, dict):
            fargs = raw_args
        else:
            fargs = {}

        # 3) เรียก tool
        tool_result = _dispatch_tool(user_info, fname, fargs)
        tool_result = _clip(tool_result)

        # 4) ส่ง FunctionResponse กลับเข้า session
        resp2 = _send_function_response(chat, fname, tool_result)

        return (getattr(resp2, "text", "") or "").strip() or tool_result

    except Exception as e:
        print(f"[process_with_function_calling] Error: {e}")
        _clear_session(user_id)  # กันลูปล้มซ้ำ ๆ
        return "อุ๊ย! สมองชิบะน้อยรวนไปแป๊บนึงครับ ลองอีกทีนะ"

def summarize_text_with_gpt(text: str) -> str:
    prompt = (
        "สรุปใจความสำคัญต่อไปนี้แบบสั้น กระชับ เป็นข้อ ๆ ไม่เกิน 6 บรรทัด "
        "ใช้ภาษาไทยล้วน เน้นสาระที่ควรเก็บไว้เป็นบริบทคุยต่อไป:\n\n"
        f"{text}"
    )
    try:
        prefer_strong = len(text) > 800
        return generate_text(prompt, prefer_strong=prefer_strong) or ""
    except Exception:
        return ""
