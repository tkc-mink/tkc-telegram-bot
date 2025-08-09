# utils/openai_client.py
# -*- coding: utf-8 -*-
"""
ตัวห่อ (wrapper) การเรียก OpenAI SDK รุ่นใหม่ (>=1.x)
- ใช้ client.chat.completions.create สำหรับแชท
- รองรับโมเดล gpt-4o / gpt-4o-mini (ค่าเริ่มต้น)
- ไม่ใช้ proxies ในโค้ด (ถ้าต้องใช้ ให้ตั้ง ENV แทน)
"""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# สร้าง client แบบ global หนึ่งตัวพอ
_client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """
    เรียก Chat Completions แบบง่าย คืนค่า text อย่างเดียว

    :param messages: [{"role":"system"|"user"|"assistant", "content":"..."}]
    :param model: ชื่อโมเดล (ถ้าไม่ใส่ ใช้ DEFAULT_MODEL)
    :param temperature: ความสุ่ม
    :param max_tokens: จำกัดโทเคนคำตอบ (None = ปล่อยตาม default)
    :return: ข้อความที่โมเดลตอบ (str)
    """
    _model = model or DEFAULT_MODEL

    resp = _client.chat.completions.create(
        model=_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()

def simple_ask(prompt: str, model: Optional[str] = None) -> str:
    """
    ทางลัด ถามด้วยข้อความเดียว (role=user) แล้วรับคำตอบกลับมา
    """
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    return chat_completion(msgs, model=model)
