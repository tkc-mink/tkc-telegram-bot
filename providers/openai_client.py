# providers/openai_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import time
import os

from config import OPENAI_API_KEY, OPENAI_MODEL_DIALOGUE

_VALID_ROLES = {"user", "assistant", "system"}

def _normalize_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """กัน role เพี้ยน/คอนเทนต์ว่าง เผื่อ input มาจากหลายที่"""
    out: List[Dict[str, str]] = []
    for m in messages or []:
        role = (m.get("role") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if role in _VALID_ROLES and content:
            out.append({"role": role, "content": content})
    return out

def call_gpt(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_output_tokens: int = 1024,
) -> str:
    """
    เรียก OpenAI Chat Completions (SDK >= 1.x)
    - ใช้คีย์/โมเดลจาก config.py
    - ถ้าคีย์หาย/ผิดพลาด → raise เพื่อให้ออเคสเตรเตอร์สลับไป Gemini ได้
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    # รองรับ BASE URL เผื่อใช้พร็อกซี/เซิร์ฟเวอร์ภายใน
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or None

    from openai import OpenAI  # import ภายในฟังก์ชัน กันล่มตอนติดตั้งไม่ครบ
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=base_url) if base_url else OpenAI(api_key=OPENAI_API_KEY)

    model = OPENAI_MODEL_DIALOGUE or "gpt-4o-mini"
    msgs = _normalize_messages(messages)

    # retry เบา ๆ กรณี rate limit/เน็ตสะดุด
    last_err: Exception | None = None
    for attempt in range(2):  # รวม 2 ครั้ง
        try:
            rsp = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=float(temperature),
                max_tokens=int(max_output_tokens),
            )
            text = (rsp.choices[0].message.content or "").strip()
            return text
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            # ลองอีกครั้งถ้าเป็นแนว 429/timeout
            if attempt == 0 and any(k in msg for k in ("429", "rate", "timeout", "overloaded")):
                time.sleep(0.8)
                continue
            break

    raise RuntimeError(f"openai_call_failed: {last_err}")
