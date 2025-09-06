# function_calling.py
# -*- coding: utf-8 -*-
"""
Function Calling Engine (Gemini, ChatSession)
- สนทนาแบบหลายเทิร์น (มีบริบทต่อเนื่อง) ด้วย Gemini v1 (google-generativeai >= 0.8.x)
- รองรับเครื่องมือเรียกข้อมูลสด: weather/gold/news/stock/oil/lottery/crypto
- Public API:
    process_with_function_calling(user_info, user_text, ctx=None, conv_summary=None) -> str
    summarize_text_with_gpt(text) -> str
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import time
from threading import RLock

import google.generativeai as genai

# --- import generate_text: รองรับทั้ง providers/ และ utils/ ---
try:
    from providers.gemini_client import generate_text as _gen_text  # แนะนำให้มีไฟล์นี้
except Exception:
    # เผื่อมี shim ไว้ใน utils/
    from utils.gemini_client import generate_text as _gen_text  # type: ignore
generate_text = _gen_text

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

# ---------- Configuration / Safety ----------
_GEMINI_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("PALM_API_KEY")
    or ""
).strip()

_TEXT_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SEC", "60"))
_MAX_TOOL_RESULT_CHARS = int(os.getenv("MAX_TOOL_RESULT_CHARS", "4000"))
_SESSION_CAP = int(os.getenv("CHAT_SESSION_CAP", "200"))

# ตั้งค่า genai.configure ถ้ามีคีย์
try:
    if _GEMINI_API_KEY:
        genai.configure(api_key=_GEMINI_API_KEY)
except Exception as _e:
    print(f"[function_calling] WARN: genai.configure failed: {_e}")

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
gemini_model_with_tools: Optional[Any] = None
if _GEMINI_API_KEY:
    try:
        # google-generativeai 0.8.x ใช้ parameter 'model_name'
        gemini_model_with_tools = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            tools=[TOOL_CONFIG],
            system_instruction=SYSTEM_PROMPT,
        )
    except Exception as e:
        print(f"[function_calling] ❌ ERROR: init GenerativeModel failed: {e}")
else:
    print("[function_calling] INFO: GOOGLE_API_KEY/GEMINI_API_KEY not set — tools chat disabled.")

# ---------- In-memory sessions (LRU + lock) ----------
CHAT_SESSIONS: Dict[int, Any] = {}
_LAST_USED: Dict[int, float] = {}
_SESS_LOCK = RLock()

# ---------- Helpers ----------
def _clip(s: str, n: int = _MAX_TOOL_RESULT_CHARS) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else (s[: n - 200].rstrip() + "\n…(ตัดเพื่อความกระชับ)")

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
            topic = str(args.get("topic", "ข่าวล่าสุด") or "ข่าวล่าสุด")
            return get_news(topic)

        if fname == "get_stock_info":
            symbol = str(args.get("symbol", "PTT.BK") or "PTT.BK").strip()
            return get_stock_info_from_google(symbol)

        if fname == "get_oil_price":
            return get_oil_price_from_google()

        if fname == "get_lottery_result":
            return get_lottery_result()

        if fname == "get_crypto_price":
            symbol = str(args.get("symbol", "BTC") or "BTC").strip()
            return get_crypto_price_from_google(symbol)

        return f"เอ๊ะ... ชิบะน้อยไม่รู้จักเครื่องมือที่ชื่อ {fname} ครับ"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return f"อุ๊ย! เครื่องมือ {fname} ของชิบะน้อยมีปัญหาซะแล้วครับ: {e}"

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
        chat = gemini_model_with_tools.start_chat(history=history)  # type: ignore[union-attr]
        CHAT_SESSIONS[user_id] = chat
        _LAST_USED[user_id] = time.time()

        # LRU eviction
        if len(CHAT_SESSIONS) > max(_SESSION_CAP, 1):
            oldest_uid = min(_LAST_USED, key=_LAST_USED.get)
            if oldest_uid != user_id:
                CHAT_SESSIONS.pop(oldest_uid, None)
                _LAST_USED.pop(oldest_uid, None)
                print(f"[ChatSession] evict user {oldest_uid}")
        return chat

def _clear_session(user_id: int) -> None:
    with _SESS_LOCK:
        CHAT_SESSIONS.pop(user_id, None)
        _LAST_USED.pop(user_id, None)

def _send_function_response(chat: Any, name: str, tool_result: str):
    """
    ส่ง FunctionResponse ให้ครอบคลุมหลายเวอร์ชัน SDK:
    - ลองใช้ genai.types.FunctionResponse ก่อน
    - ถ้าไม่สำเร็จ ตกลงมาใช้ dict {"function_response": {...}}
    """
    try:
        payload = genai.types.FunctionResponse(name=name, response={"result": tool_result})
        return chat.send_message(part=payload, request_options={"timeout": _TEXT_TIMEOUT})
    except Exception:
        return chat.send_message(
            {"function_response": {"name": name, "response": {"result": tool_result}}},
            request_options={"timeout": _TEXT_TIMEOUT},
        )

def _find_function_call_in_parts(parts: Any) -> Optional[Any]:
    """วนหา part ที่มี function_call ในโครงสร้าง parts"""
    if not parts:
        return None
    for p in parts:
        if getattr(p, "function_call", None):
            return p
        if isinstance(p, dict) and "function_call" in p:
            return p
    return None

def _extract_function_call(resp: Any) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    คืน (fname, fargs) หากมี function_call; ไม่งั้น (None, {})
    รองรับหลายรูปแบบ response ของ SDK
    """
    # 1) บน resp.parts
    try:
        p = _find_function_call_in_parts(getattr(resp, "parts", None))
        if p:
            fc = getattr(p, "function_call", None) or p.get("function_call")
            name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
            raw_args = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else None)
            if hasattr(raw_args, "items"):
                args = {k: v for k, v in raw_args.items()}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
            return name, args
    except Exception:
        pass

    # 2) เผื่ออยู่ใน candidates[].content.parts
    try:
        for c in getattr(resp, "candidates", []) or []:
            content = getattr(c, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            p = _find_function_call_in_parts(parts)
            if p:
                fc = getattr(p, "function_call", None) or p.get("function_call")
                name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
                raw_args = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else None)
                if hasattr(raw_args, "items"):
                    args = {k: v for k, v in raw_args.items()}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}
                return name, args
    except Exception:
        pass

    return None, {}

# ---------- Public API ----------
def process_with_function_calling(
    user_info: Dict[str, Any],
    user_text: str,
    ctx: List[Dict[str, str]] | None = None,
    conv_summary: str | None = None,
) -> str:
    # แจ้งชัดเจนหากยังไม่มีคีย์
    if not _GEMINI_API_KEY:
        return ("ตอนนี้ชิบะน้อยยังเรียกสมอง Gemini ไม่ได้ครับ "
                "เพราะยังไม่ได้ตั้งค่า GOOGLE_API_KEY (หรือ GEMINI_API_KEY) บนเซิร์ฟเวอร์ "
                "ให้ผู้ดูแลตั้งค่าแล้วลองใหม่อีกครั้งนะครับ")

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
        resp = chat.send_message(user_text, request_options={"timeout": _TEXT_TIMEOUT})

        # 2) ถ้าไม่มี parts ให้ fallback ส่งข้อความธรรมดา
        if not getattr(resp, "parts", None) and not getattr(resp, "candidates", None):
            return (getattr(resp, "text", "") or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        # 3) หา function_call ถ้ามี
        fname, fargs = _extract_function_call(resp)
        if not fname:
            return (getattr(resp, "text", "") or "").strip() or "ขอโทษครับ ผมยังตอบไม่ได้ในตอนนี้ ลองใหม่อีกครั้งนะครับ"

        # 4) เรียก tool
        tool_result = _clip(_dispatch_tool(user_info, fname, fargs))

        # 5) ส่ง FunctionResponse กลับเข้า session
        resp2 = _send_function_response(chat, fname, tool_result)

        # 6) คืนผลลัพธ์สุดท้าย
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
