# orchestrator/orchestrate.py
# -*- coding: utf-8 -*-
"""
Minimal, safe orchestrator
- จัดรูทถาม/ตอบไป GPT หรือ Gemini แบบ heuristic
- ไม่พึ่ง aggregator ใด ๆ (กันล่ม) แต่เผื่อ hook ไว้
"""

from __future__ import annotations
from typing import List, Dict, Any
import os
import re
from providers.openai_client import call_gpt
from providers.gemini_client import call_gemini

# heuristics แบบเบา ๆ (คุ้มครองเคสไทย)
LOOKUP_HINTS = [
    "ราคาทอง", "ทอง", "ราคาน้ำมัน", "น้ำมัน", "หุ้น", "ราคา", "พยากรณ์อากาศ",
    "อากาศ", "ข่าว", "exchange", "crypto", "คริปโต", "BTC", "ETH",
]

def _route(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if not t:
        return {"engine": "gpt", "confidence": 0.6, "reason": "empty"}
    # ถ้าดูเป็นข้อมูลจริง/ราคา/พยากรณ์ → ให้ Gemini นำ
    if any(k.lower() in t.lower() for k in LOOKUP_HINTS):
        return {"engine": "gemini", "confidence": 0.7, "reason": "lookup_like"}
    # ค่าเริ่มต้น: ให้ GPT ทำ reasoning/โครงสร้างภาษา
    return {"engine": "gpt", "confidence": 0.65, "reason": "reasoning_default"}

_SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' ผู้ช่วยที่พูดไทย สุภาพ กระชับ ไม่ทวนคำถาม ไม่ขึ้นต้นด้วยคำว่า 'รับทราบ' "
    "ถ้าข้อมูลไม่แน่ใจ ให้บอกอย่างซื่อสัตย์และเสนอแนวทางถามต่อ"
)

def orchestrate(text: str, context: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    route = _route(text)
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for m in (context or []):
        if m.get("role") in ("user", "assistant", "system") and m.get("content"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": text})

    engine = route["engine"]
    meta = {"route": engine, "confidence": route["confidence"], "reason": route["reason"], "fallback": None}

    try:
        if engine == "gemini":
            out = call_gemini(msgs)
        else:
            out = call_gpt(msgs)
        if not out:
            raise RuntimeError("empty_output")
        return {"text": out, "meta": meta}
    except Exception as e:
        # fallback สลับอีกตัวอัตโนมัติ
        meta["fallback"] = str(e) or "error"
        try:
            if engine == "gemini":
                out = call_gpt(msgs)
            else:
                out = call_gemini(msgs)
            return {"text": out or "ขออภัยครับ ผมยังตอบไม่ได้ในตอนนี้", "meta": meta}
        except Exception as e2:
            meta["fallback"] += f" | second_error={e2}"
            return {"text": "ขออภัยครับ ผมเจอปัญหาระหว่างประมวลผล", "meta": meta}
