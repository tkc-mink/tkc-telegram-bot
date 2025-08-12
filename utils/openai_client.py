# utils/openai_client.py
# -*- coding: utf-8 -*-
"""
OpenAI client (SDK v1.x) แบบเสถียร + Smart Model Picker

- ไม่ส่ง proxies เข้า httpx (กัน TypeError: unexpected keyword 'proxies')
- รองรับ BASE_URL/ORG/timeout/max_retries ผ่าน ENV
- มี helper:
    - chat_completion / simple_ask            : ข้อความล้วน
    - chat_completion_smart                   : สลับโมเดลอัตโนมัติ mini <-> strong
    - chat_with_tools_smart                   : เหมาะกับ function calling (tools)
    - vision_analyze                          : วิเคราะห์ภาพ (multimodal)
    - image_generate_file                     : สร้างภาพเป็นไฟล์ PNG
- รวมข้อความ error เป็นภาษาคนด้วย _err_to_text

ENV:
  OPENAI_API_KEY          (จำเป็น)
  OPENAI_MODEL            ดีฟอลต์ gpt-5-mini        <-- แนะนำตั้งค่านี้
  OPENAI_MODEL_STRONG     ดีฟอลต์ gpt-5             <-- งานยาก/สำคัญ
  OPENAI_MODEL_VISION     ดีฟอลต์ gpt-4o-mini
  OPENAI_MODEL_IMAGE      ดีฟอลต์ gpt-image-1
  OPENAI_BASE_URL         หากใช้ gateway ภายใน (เช่น https://api.your-proxy/v1)
  OPENAI_ORG              ถ้ามี
  OPENAI_TIMEOUT_SEC      ดีฟอลต์ 30
  OPENAI_MAX_RETRIES      ดีฟอลต์ 3
"""

from __future__ import annotations
import os
import base64
import time
from typing import List, Dict, Any, Optional

from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, AuthenticationError

# ===== ENV =====
API_KEY       = os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL      = os.getenv("OPENAI_BASE_URL", "").strip() or None
ORG           = os.getenv("OPENAI_ORG", "").strip() or None

# --- โมเดลหลัก ---
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")    # << ดีฟอลต์ใหม่
STRONG_MODEL  = os.getenv("OPENAI_MODEL_STRONG", "gpt-5")  # << ใช้กับงานยาก
VISION_MODEL  = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
IMAGE_MODEL   = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1")

TIMEOUT       = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))
MAX_RETRIES   = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

if not API_KEY:
    print("[openai_client] WARNING: OPENAI_API_KEY is not set")

# ===== Build client (ห้ามส่ง proxies) =====
_client_kwargs: Dict[str, Any] = {
    "api_key": API_KEY,
    "timeout": TIMEOUT,
    "max_retries": MAX_RETRIES,
}
if BASE_URL:
    _client_kwargs["base_url"] = BASE_URL
if ORG:
    _client_kwargs["organization"] = ORG

client = OpenAI(**_client_kwargs)  # ✅ no proxies


# ===== Error helper =====
def _err_to_text(e: Exception) -> str:
    if isinstance(e, (APITimeoutError, )):
        return "❌ หมดเวลาเชื่อมต่อบริการ AI กรุณาลองใหม่อีกครั้ง (timeout)"
    if isinstance(e, (RateLimitError, )):
        return "❌ มีการใช้งานหนาแน่น (rate limit) กรุณาลองใหม่อีกครั้งครับ"
    if isinstance(e, (AuthenticationError, )):
        return "❌ API key ไม่ถูกต้องหรือหมดสิทธิ์ กรุณาตรวจสอบค่า OPENAI_API_KEY"
    if isinstance(e, (APIError, )):
        return f"❌ บริการ AI ขัดข้อง: {getattr(e, 'message', str(e))}"
    return f"❌ ข้อผิดพลาดไม่ทราบสาเหตุ: {e}"


# ====== Smart model picker ======
HARD_KEYWORDS = [
    "วิเคราะห์เชิงลึก", "พิสูจน์", "ซับซ้อน", "โจทย์ยาก", "ออกแบบสถาปัตยกรรม",
    "เขียนโค้ด", "refactor", "optimize", "algorithm", "big-o", "regex",
    "ทดสอบหน่วย", "unit test", "sql", "schema", "กฎหมาย", "วางกลยุทธ์", "แผนธุรกิจ"
]

def pick_model(prompt: Optional[str] = None, force: Optional[str] = None) -> str:
    """
    เลือกโมเดลอัตโนมัติ:
      - ถ้าระบุ force -> ใช้ตามนั้น
      - ถ้าไม่มี prompt -> DEFAULT_MODEL
      - ถ้าเจอ keyword/ยาวมาก/มี code block -> STRONG_MODEL
    """
    if force:
        return force
    if not prompt:
        return DEFAULT_MODEL
    text = (prompt or "").lower()
    hard = any(k in text for k in HARD_KEYWORDS)
    hard = hard or len(prompt) > 1200 or "```" in prompt or "SELECT " in prompt or "CREATE TABLE" in prompt
    return STRONG_MODEL if hard else DEFAULT_MODEL


# ===== Chat (ข้อความอย่างเดียว) =====
def chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """เรียก chat.completions และคืนเฉพาะข้อความตอบกลับ"""
    _model = model or DEFAULT_MODEL
    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return _err_to_text(e)


def chat_completion_smart(
    messages: List[Dict[str, Any]],
    prefer_strong: bool = False,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """
    เรียกแชทแบบเลือกโมเดลอัตโนมัติ + fallback:
      - ปกติใช้ DEFAULT_MODEL (gpt-5-mini)
      - ถ้าข้อความยาก/ยาว หรือ prefer_strong=True -> ยกไป STRONG_MODEL (gpt-5)
      - ถ้า error จะลองสลับโมเดลอีกฝั่งหนึ่งให้อัตโนมัติ
    """
    # หา user prompt ล่าสุด
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = str(m.get("content") or "")
            break

    model = STRONG_MODEL if prefer_strong else pick_model(user_txt)
    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e1:
        # ลองอีกโมเดลหนึ่งเป็นสำรอง
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        try:
            resp = client.chat.completions.create(
                model=backup, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e2:
            return _err_to_text(e2)


def chat_with_tools_smart(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_choice: str = "auto",
    prefer_strong: bool = False,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> Any:
    """
    สะดวกใช้กับ Function Calling:
      - เลือกโมเดลอัตโนมัติ (หรือ force strong)
      - ส่งกลับ response object (เผื่อผู้ใช้ต้องอ่าน tool_calls เอง)
      - มี fallback สลับโมเดลให้
    """
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = str(m.get("content") or "")
            break

    model = STRONG_MODEL if prefer_strong else pick_model(user_txt)
    try:
        return client.chat.completions.create(
            model=model, messages=messages, tools=tools,
            tool_choice=tool_choice, temperature=temperature, max_tokens=max_tokens
        )
    except Exception:
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        return client.chat.completions.create(
            model=backup, messages=messages, tools=tools,
            tool_choice=tool_choice, temperature=temperature, max_tokens=max_tokens
        )


def simple_ask(prompt: str, model: Optional[str] = None) -> str:
    """ถามสั้น ๆ (role=user)"""
    msgs = [
        {"role": "system", "content": "You are a helpful, concise assistant."},
        {"role": "user", "content": prompt},
    ]
    # ใช้ smart picker ถ้าไม่บังคับโมเดล
    if model:
        return chat_completion(msgs, model=model)
    return chat_completion_smart(msgs)


# ===== Vision (วิเคราะห์ภาพ) =====
def vision_analyze(
    image_urls_or_dataurls: List[str],
    prompt: str = "Analyze this image in Thai, be concise.",
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    """
    ส่งรายการรูป (URL หรือ dataURL) ให้โมเดล Vision วิเคราะห์
    - image_urls_or_dataurls: ["data:image/png;base64,...", "https://..."]
    """
    _model = model or VISION_MODEL
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for u in image_urls_or_dataurls:
        content.append({"type": "image_url", "image_url": {"url": u}})
    messages = [{"role": "user", "content": content}]
    try:
        resp = client.chat.completions.create(
            model=_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return _err_to_text(e)


# ===== Image Generation (สร้างภาพ) =====
def image_generate_file(
    prompt: str,
    size: str = "1024x1024",
    out_path: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    """
    สร้างภาพด้วย gpt-image-1 แล้วบันทึกไฟล์เป็น PNG
    คืน path ของไฟล์ที่บันทึก หรือ None หากผิดพลาด
    """
    _model = model or IMAGE_MODEL
    try:
        res = client.images.generate(model=_model, prompt=prompt, size=size)
        b64 = res.data[0].b64_json
        img_bytes = base64.b64decode(b64)
        out_path = out_path or "generated.png"
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        return out_path
    except Exception as e:
        print("[openai_client.image_generate_file] error:", e)
        return None
