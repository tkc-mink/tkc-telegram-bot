# utils/openai_client.py
# -*- coding: utf-8 -*-
"""
Wrapper สำหรับ OpenAI SDK v1.x
- ไม่ใช้ proxies ในโค้ด (ถ้าจำเป็นตั้ง ENV: HTTP_PROXY/HTTPS_PROXY)
- รองรับ BASE_URL/organization ผ่าน ENV
- ใส่ timeout / max_retries และจับ error คืนข้อความที่อ่านง่าย
ENV ที่รองรับ:
    OPENAI_API_KEY          (จำเป็น)
    OPENAI_MODEL            ดีฟอลต์ gpt-4o-mini
    OPENAI_BASE_URL         ถ้าคุณใช้ gateway ภายใน เช่น https://api.your-proxy/v1
    OPENAI_ORG              ถ้าองค์กรคุณตั้งไว้
    OPENAI_TIMEOUT_SEC      ดีฟอลต์ 30
    OPENAI_MAX_RETRIES      ดีฟอลต์ 3
"""

from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, AuthenticationError

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
ORG      = os.getenv("OPENAI_ORG", "").strip() or None
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

TIMEOUT = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

if not API_KEY:
    print("[openai_client] WARNING: OPENAI_API_KEY is not set")

_client_kwargs: Dict[str, Any] = {
    "api_key": API_KEY,
    "timeout": TIMEOUT,
    "max_retries": MAX_RETRIES,
}
if BASE_URL:
    _client_kwargs["base_url"] = BASE_URL
if ORG:
    _client_kwargs["organization"] = ORG

client = OpenAI(**_client_kwargs)  # ❌ ห้ามใส่ proxies ที่นี่


def chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """เรียก Chat Completions แล้วคืนข้อความอย่างเดียว"""
    _model = model or DEFAULT_MODEL
    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except (APITimeoutError, RateLimitError) as e:
        return f"❌ ระบบคิวแน่นหรือหมดเวลา ลองใหม่อีกครั้งครับ ({type(e).__name__})"
    except AuthenticationError:
        return "❌ API key ใช้งานไม่ได้ กรุณาตรวจสอบค่า OPENAI_API_KEY"
    except APIError as e:
        # ข้อผิดพลาดฝั่ง API (5xx ฯลฯ)
        return f"❌ เกิดข้อผิดพลาดจากบริการ AI: {getattr(e, 'message', str(e))}"
    except Exception as e:
        return f"❌ เกิดข้อผิดพลาดไม่ทราบสาเหตุ: {e}"


def simple_ask(prompt: str, model: Optional[str] = None) -> str:
    """ถามด้วยข้อความเดียว (role=user) แล้วรับคำตอบกลับมา"""
    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    return chat_completion(msgs, model=model)
