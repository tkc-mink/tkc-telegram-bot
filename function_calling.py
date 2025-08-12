# src/function_calling.py
# -*- coding: utf-8 -*-

import os
import json
from typing import List, Dict, Any, Optional

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
from utils.prompt_templates import SYSTEM_NO_ECHO  # ห้ามทวนคำถาม
import re

# ---------- Tools ----------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "ดูพยากรณ์อากาศวันนี้หรืออากาศล่วงหน้าในไทย",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "ข้อความที่ผู้ใช้พิมพ์"},
                    "lat":  {"type": "number", "description": "ละติจูด (ถ้ามี)", "nullable": True},
                    "lon":  {"type": "number", "description": "ลองจิจูด (ถ้ามี)", "nullable": True},
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
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
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
                    "topic": {"type": "string", "description": "หัวข้อข่าว"},
                    "limit": {"type": "integer", "description": "จำนวนข่าว (1-10)", "default": 5}
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
                    "query": {"type": "string", "description": "ชื่อหุ้น หรือ SET หรือสัญลักษณ์เช่น PTT.BK"}
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
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lottery_result",
            "description": "ผลสลากกินแบ่งรัฐบาลล่าสุด",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
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
                    "coin": {"type": "string", "description": "ชื่อเหรียญ เช่น BTC, ETH, SOL"}
                },
                "required": ["coin"]
            }
        }
    },
]

# ---------- บุคลิกบอท ----------
SYSTEM_PROMPT = (
    "คุณเป็นผู้ช่วยภาษาไทย ตอบสั้น กระชับ ตรงประเด็น เป็นมิตร "
    "ห้ามทวนคำถามหรือคัดลอกคำของผู้ใช้ก่อนตอบ "
    "อย่าแนะนำตัวเอง เว้นแต่ผู้ใช้ถามชื่อ โดยให้ตอบสั้น ๆ เท่านั้น "
    "อย่าเสนอหัวข้อ/ทำเมนูเอง ยกเว้นผู้ใช้ร้องขอ 'ขอไอเดีย/ตัวเลือก' ชัดเจน "
    "หากพบคำถามเกี่ยวกับอากาศ ราคาทอง ข่าว หุ้น น้ำมัน หวย หรือคริปโต ให้เรียกเครื่องมือที่มีให้"
)

# ---------- dispatch tools ----------
def function_dispatch(fname: str, args: Dict[str, Any]) -> str:
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
        return "❌ ฟังก์ชันนี้ยังไม่รองรับในระบบ"
    except Exception as e:
        print(f"[function_dispatch] {fname} error: {e}")
        return "❌ ดึงข้อมูลจากฟังก์ชันไม่สำเร็จ"

# ---------- context helpers ----------
def _normalize_context(ctx) -> List[Dict[str, str]]:
    if not ctx:
        return []
    out = []
    for m in ctx:
        if isinstance(m, dict) and "role" in m and "content" in m:
            out.append({"role": m["role"], "content": m["content"]})
        elif isinstance(m, str):
            out.append({"role": "user", "content": m})
    return out[-12:]

# ---------- sanitizer (กันทวน) ----------
_PREFIX_REGEX = re.compile("|".join([
    r"^\s*รับทราบ[:：-]\s*",
    r"^\s*คุณ\s*ถามว่า[:：-]\s*",
    r"^\s*สรุปคำถาม[:：-]\s*",
    r"^\s*ยืนยันคำถาม[:：-]\s*",
    r"^\s*คำถามของคุณ[:：-]\s*",
    r"^\s*Question[:：-]\s*",
    r"^\s*You\s+asked[:：-]\s*",
]), re.IGNORECASE | re.UNICODE)

def _strip_prefix(s: str) -> str:
    return _PREFIX_REGEX.sub("", s or "", count=1)

def _sanitize_no_echo(user_text: str, reply: str) -> str:
    if not reply:
        return reply
    reply = _strip_prefix(reply).lstrip()
    lines = reply.splitlines()
    if not lines:
        return reply
    def _norm(x: str) -> str:
        import re as _re
        x = _re.sub(r"[\"'`“”‘’\s]+", "", x, flags=_re.UNICODE)
        x = _re.sub(r"[.。…!?！？]+$", "", x, flags=_re.UNICODE)
        return x.casefold()
    if _norm(lines[0]).startswith(_norm(user_text)[: max(1, int(len(user_text)*0.85)) ]):
        lines = lines[1:]
        if lines:
            lines[0] = _strip_prefix(lines[0]).lstrip()
    return ("\n".join(line.rstrip() for line in lines)).strip() or reply.strip()

# ---------- core ----------
def process_with_function_calling(
    user_message: str,
    ctx=None,
    conv_summary: Optional[str] = None,
    debug: bool = False,
) -> str:
    """
    ตอบด้วย LLM + tools โดยอาศัยบริบท (ctx) และสรุปบทสนทนา (conv_summary)
    """
    try:
        text = user_message or ""
        low = text.casefold()

        if any(k in low for k in ["ชื่ออะไร", "คุณชื่ออะไร", "คุณคือใคร", "bot ชื่ออะไร", "/start"]):
            return bot_intro()

        force_model: Optional[str] = None
        if low.startswith("/gpt5 "):
            force_model = STRONG_MODEL
            text = text.split(" ", 1)[1]
        elif "ใช้ gpt5" in low or "use gpt5" in low:
            force_model = STRONG_MODEL

        # ใส่ No-Echo ก่อน + บุคลิก + บทสรุป (ถ้ามี) + บริบทล่าสุด
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_NO_ECHO},
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        if conv_summary:
            messages.append({"role": "system", "content": f"[บทสรุปก่อนหน้า]\n{conv_summary.strip()}"} )
        if ctx:
            messages.extend(_normalize_context(ctx))
        messages.append({"role": "user", "content": text})

        model = force_model or pick_model(text)

        # รอบแรก
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=TOOLS, tool_choice="auto"
            )
        except Exception:
            alt = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
            resp = client.chat.completions.create(
                model=alt, messages=messages, tools=TOOLS, tool_choice="auto"
            )
            model = alt

        msg = resp.choices[0].message

        # ไม่มี tool
        if not getattr(msg, "tool_calls", None):
            answer = (msg.content or "").strip() or "❌ ไม่พบข้อความตอบกลับ"
            return adjust_bot_tone(_sanitize_no_echo(text, answer))

        # มี tool
        tool_calls = msg.tool_calls or []
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        last_result = None
        for tc in tool_calls:
            fname = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            result_text = function_dispatch(fname, args)
            last_result = result_text
            messages.append({"role": "tool", "tool_call_id": tc.id, "name": fname, "content": result_text})

        try:
            resp2 = client.chat.completions.create(model=model, messages=messages, tool_choice="none")
        except Exception:
            alt = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
            resp2 = client.chat.completions.create(model=alt, messages=messages, tool_choice="none")

        final = (resp2.choices[0].message.content or "").strip()
        final = _sanitize_no_echo(text, final if final else (last_result or ""))

        if debug:
            try:
                print("=== CTX ===");  print(json.dumps(messages, ensure_ascii=False)[:2000])
                print("=== FINAL ==="); print(final)
            except Exception: pass

        return adjust_bot_tone(final)

    except Exception as e:
        print(f"[process_with_function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"

# ---------- สรุปข้อความ ----------
def summarize_text_with_gpt(text: str) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_NO_ECHO},
            {"role": "system", "content": "ช่วยสรุปเนื้อหานี้ให้สั้น กระชับ เป็นภาษาไทย"},
            {"role": "user", "content": text}
        ]
        resp = client.chat.completions.create(model=DEFAULT_MODEL, messages=messages)
        msg = resp.choices[0].message
        out = (msg.content or "").strip() or "❌ ไม่พบข้อความสรุป"
        return _sanitize_no_echo(text, out)
    except Exception as e:
        print(f"[summarize_text_with_gpt] {e}")
        return "❌ สรุปข้อความไม่สำเร็จ"
