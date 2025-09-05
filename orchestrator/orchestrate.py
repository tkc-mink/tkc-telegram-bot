# orchestrator/orchestrate.py
# -*- coding: utf-8 -*-
"""
Shiba Orchestrator
- เลือกใช้ GPT หรือ Gemini ตาม "intent" ของคำถาม (reasoning vs lookup)
- เคารพโหมดบังคับจาก ENV: ROUTER_MODE = hybrid|gpt|gemini
- มี fallback อัตโนมัติข้ามค่ายเมื่อเกิดข้อผิดพลาด/ผลลัพธ์ว่าง
- ไม่ทำให้แอปล่มถ้ายังไม่มีคีย์ฝั่งใดฝั่งหนึ่ง (orchestrate จะ fallback ให้เอง)
- ปลอดภัย: ตัด prefix แนว "รับทราบ:/คุณถามว่า:" ออก และจำกัดความยาวผลลัพธ์
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple
import re
import time

from config import (
    ROUTER_MODE,
    ROUTER_MIN_CONFIDENCE,
    OPENAI_MODEL_DIALOGUE,
    GEMINI_MODEL_DIALOGUE,
)

# providers (ต้องมีตามที่เราวางไว้)
from providers.openai_client import call_gpt
from providers.gemini_client import call_gemini

# --- optional postprocess (ถ้าไม่มีไฟล์นี้ ก็ใช้ noop) ---
try:
    from utils.postprocess import strip_no_echo_prefix as _strip_no_echo_prefix  # type: ignore
except Exception:
    def _strip_no_echo_prefix(s: str) -> str:  # noqa: E306
        return s or ""

try:
    from utils.postprocess import safe_truncate as _safe_truncate  # type: ignore
except Exception:
    def _safe_truncate(s: str, n: int = 3900) -> str:  # noqa: E306
        s = s or ""
        return s if len(s) <= n else s[:n]

# ---------- persona / system prompt ----------
_SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' ผู้ช่วยภาษาไทยที่สุภาพ กระชับ ไม่ทวนคำถาม และซื่อสัตย์ "
    "หากข้อมูลไม่แน่ใจให้บอกตรง ๆ และเสนอแนวทางค้น/ตรวจสอบต่อไปได้เอง "
    "คำตอบควรกระชับ ใช้หัวข้อ/บูลเลตเท่าที่จำเป็น และอย่าเริ่มด้วยคำว่า 'รับทราบ' หรือการทวนคำถาม"
)

# ---------- intent & routing ----------
_LOOKUP_HINTS = [
    # ไทย
    "ราคาทอง", "ทอง", "ราคาน้ำมัน", "น้ำมัน", "หุ้น", "ดัชนี", "ราคา", "พยากรณ์อากาศ",
    "อากาศ", "ข่าว", "คริปโต", "เหรียญ", "หวย", "สลาก", "น้ำมัน", "เรท",
    # อังกฤษ/สากล
    "price", "prices", "stock", "index", "indices", "exchange", "crypto", "btc", "eth", "weather",
]

_WRITING_HINTS = [
    "เขียน", "สรุป", "สรุปให้", "เรียบเรียง", "ร่าง", "แก้สำนวน",
    "improve", "rewrite", "summarize", "draft", "tone", "polish",
]

def _classify_intent(text: str) -> Tuple[str, float, str]:
    """
    คืน (intent, confidence, reason)
    intent: "lookup" | "reasoning" | "writing"
    """
    t = (text or "").strip().lower()
    if not t:
        return ("reasoning", 0.55, "empty")

    if any(k in t for k in (kw.lower() for kw in _WRITING_HINTS)):
        return ("writing", 0.68, "writing_like")

    if any(k in t for k in (kw.lower() for kw in _LOOKUP_HINTS)):
        return ("lookup", 0.70, "lookup_like")

    # คำถามเชิงเหตุผลทั่วไป
    return ("reasoning", 0.62, "default_reasoning")

def _route_engine(text: str) -> Dict[str, Any]:
    """
    ตัดสินใจเลือก engine ตาม intent/โหมด
    """
    intent, conf, why = _classify_intent(text)

    # โหมดบังคับจาก ENV
    mode = (ROUTER_MODE or "hybrid").strip().lower()
    if mode == "gpt":
        return {"engine": "gpt", "intent": intent, "confidence": max(conf, 0.99), "reason": f"forced:gpt/{why}"}
    if mode == "gemini":
        return {"engine": "gemini", "intent": intent, "confidence": max(conf, 0.99), "reason": f"forced:gemini/{why}"}

    # hybrid:
    if intent == "lookup":
        return {"engine": "gemini", "intent": intent, "confidence": conf, "reason": why}
    # งานเขียน/ภาษา → GPT เด่น
    if intent == "writing":
        return {"engine": "gpt", "intent": intent, "confidence": conf, "reason": why}
    # เหตุผลทั่วไปให้ GPT นำ
    return {"engine": "gpt", "intent": intent, "confidence": conf, "reason": why}

# ---------- utility ----------
_VALID_ROLES = {"user", "assistant", "system"}

def _normalize_context(ctx: List[Dict[str, str]] | None) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    if not ctx:
        return out
    for m in ctx:
        r = (m.get("role") or "").strip().lower()
        c = (m.get("content") or "").strip()
        if r in _VALID_ROLES and c:
            out.append({"role": r, "content": c})
    return out

def _looks_like_config_error(s: str) -> bool:
    if not s:
        return True
    t = s.lower()
    return (
        "ยังไม่ได้ตั้งค่า" in t
        or "api key" in t
        or "unauthorized" in t
        or "invalid api key" in t
        or "missing" in t and "key" in t
    )

def _ok(text: str) -> bool:
    if not text:
        return False
    if len(text.strip()) < 2:
        return False
    if _looks_like_config_error(text):
        return False
    return True

# ---------- main ----------
def orchestrate(text: str, context: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    """
    รับข้อความผู้ใช้ + บริบท แล้วคืน {"text": <คำตอบ>, "meta": {...}}
    meta: route, intent, confidence, model_used, fallback, durations (ms)
    """
    route = _route_engine(text)
    primary = route["engine"]            # "gpt" | "gemini"
    fallback = "gemini" if primary == "gpt" else "gpt"

    msgs = _normalize_context(context)
    msgs.append({"role": "user", "content": text})

    meta: Dict[str, Any] = {
        "intent": route["intent"],
        "route": primary,
        "confidence": route["confidence"],
        "reason": route["reason"],
        "model_candidates": {
            "gpt": OPENAI_MODEL_DIALOGUE,
            "gemini": GEMINI_MODEL_DIALOGUE,
        },
        "fallback": None,
        "durations_ms": {},
    }

    # ความเชื่อมั่นต่ำมาก → ลองสลับใช้ GPT เป็นค่าเริ่ม (ภาษากว้าง)
    if route["confidence"] < float(ROUTER_MIN_CONFIDENCE or 0.55):
        primary, fallback = "gpt", "gemini"
        meta["route"] = primary
        meta["reason"] += "|low_conf->prefer_gpt"

    # ---- call primary ----
    t0 = time.time()
    try:
        if primary == "gemini":
            out = call_gemini(msgs)
        else:
            out = call_gpt(msgs)
        meta["durations_ms"]["primary"] = int((time.time() - t0) * 1000)
        if _ok(out):
            final = _safe_truncate(_strip_no_echo_prefix(out), 3900)
            meta["model_used"] = primary
            return {"text": final, "meta": meta}
        else:
            meta["primary_empty_or_config"] = True
    except Exception as e:
        meta["primary_error"] = str(e)

    # ---- fallback ----
    t1 = time.time()
    try:
        if fallback == "gemini":
            out2 = call_gemini(msgs)
        else:
            out2 = call_gpt(msgs)
        meta["durations_ms"]["fallback"] = int((time.time() - t1) * 1000)
        if _ok(out2):
            final = _safe_truncate(_strip_no_echo_prefix(out2), 3900)
            meta["model_used"] = fallback
            meta["fallback"] = True
            return {"text": final, "meta": meta}
        else:
            meta["fallback_empty_or_config"] = True
    except Exception as e2:
        meta["fallback_error"] = str(e2)
        meta["fallback"] = False

    # ---- both failed ----
    apology = (
        "ขออภัยครับ ผมเจอปัญหาระหว่างประมวลผลคำขอนี้ "
        "รบกวนลองใหม่อีกครั้ง หรือระบุรายละเอียดเพิ่มเติมได้ไหมครับ"
    )
    return {"text": apology, "meta": meta}
