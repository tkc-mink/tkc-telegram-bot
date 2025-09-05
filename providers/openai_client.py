# providers/openai_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import os

def call_gpt(messages: List[Dict[str, str]]) -> str:
    """
    เรียก OpenAI (SDK v1.x)
    ENV:
      OPENAI_API_KEY
      OPENAI_MODEL_DIALOGUE (default: gpt-4o-mini)
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "ยังไม่ได้ตั้งค่า OPENAI_API_KEY ครับ"

    model = os.getenv("OPENAI_MODEL_DIALOGUE", "gpt-4o-mini")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        rsp = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
        return (rsp.choices[0].message.content or "").strip()
    except Exception as e:
        raise
