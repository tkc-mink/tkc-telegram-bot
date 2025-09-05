# utils/openai_client.py
# -*- coding: utf-8 -*-
"""
OpenAI client (SDK v1.x) — เสถียร, ไม่ทวนคำถาม (No-Echo), เลือกโมเดลอัตโนมัติ, มี fallback
------------------------------------------------------------------------------------------
สิ่งที่ได้:
- แทรก System Prompt แบบ "ไม่ทวนคำถาม" อัตโนมัติ (SYSTEM_NO_ECHO)
- เลือกโมเดลอัตโนมัติจากความยากของโจทย์ (gpt-5-mini เป็นดีฟอลต์, ยาก → gpt-5)
- ฟังก์ชันยิงง่าย: chat_no_echo(), simple_ask()
- รองรับ tools/function calling + fallback ข้ามโมเดล
- Vision: วิเคราะห์ภาพจาก URL/dataURL (พร้อม helper แปลง bytes → dataURL)
- Image generation: คืนไฟล์ PNG พร้อม path
- จัดการข้อผิดพลาดเป็นมิตร (ไทย) + timeout/retry ผ่าน SDK

ENV ที่รองรับ:
  OPENAI_API_KEY          (จำเป็น)
  OPENAI_MODEL            ดีฟอลต์ gpt-5-mini
  OPENAI_MODEL_STRONG     ดีฟอลต์ gpt-5
  OPENAI_MODEL_VISION     ดีฟอลต์ gpt-4o-mini
  OPENAI_MODEL_IMAGE      ดีฟอลต์ gpt-image-1
  OPENAI_BASE_URL         (หากใช้ proxy/gateway)
  OPENAI_ORG              (ถ้ามี)
  OPENAI_TIMEOUT_SEC      ดีฟอลต์ 30
  OPENAI_MAX_RETRIES      ดีฟอลต์ 3
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Iterable

import os
import base64

# ---- OpenAI SDK ----
try:
    from openai import OpenAI
    # บางเวอร์ชันของ SDK แยกชนิด error ไม่เหมือนกัน จัด alias แบบปลอดภัย
    try:
        from openai import (
            APIError,
            RateLimitError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            APIConnectionError,
            APIStatusError,
        )
    except Exception:  # pragma: no cover
        APIError = Exception             # type: ignore
        RateLimitError = Exception       # type: ignore
        APITimeoutError = Exception      # type: ignore
        AuthenticationError = Exception  # type: ignore
        BadRequestError = Exception      # type: ignore
        APIConnectionError = Exception   # type: ignore
        APIStatusError = Exception       # type: ignore
except Exception as _e:  # pragma: no cover
    raise RuntimeError("ไม่พบแพ็กเกจ openai (v1.x). โปรดติดตั้งด้วย: pip install openai>=1.0.0") from _e

# ---- System / Templates (no-echo) ----
try:
    from utils.prompt_templates import SYSTEM_NO_ECHO
except Exception:
    SYSTEM_NO_ECHO = (
        "คุณเป็นผู้ช่วยที่ตอบสั้น กระชับ และตรงคำถาม "
        "ห้ามทวนคำถามหรือคัดลอกข้อความของผู้ใช้กลับมาก่อนตอบ "
        "ตอบทันทีเป็นประเด็น ไม่ต้องขึ้นต้นด้วยคำว่า 'รับทราบ' หรือ 'คุณถามว่า' "
        "หลีกเลี่ยงคำฟุ่มเฟือย และเน้นตอบเนื้อหาหลักเท่านั้น"
    )

# ======================
# ENV / Client Settings
# ======================
API_KEY       = os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL      = (os.getenv("OPENAI_BASE_URL", "") or None)
ORG           = (os.getenv("OPENAI_ORG", "") or None)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
STRONG_MODEL  = os.getenv("OPENAI_MODEL_STRONG", "gpt-5").strip()
VISION_MODEL  = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini").strip()
IMAGE_MODEL   = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1").strip()

TIMEOUT       = float(os.getenv("OPENAI_TIMEOUT_SEC", "30"))
MAX_RETRIES   = int(os.getenv("OPENAI_MAX_RETRIES", "3"))

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

client = OpenAI(**_client_kwargs)

# ================
# Error Utilities
# ================
def _err_to_text(e: Exception) -> str:
    # ไล่ชนิด error ที่พบบ่อยใน SDK v1.x
    if isinstance(e, APITimeoutError):
        return "❌ หมดเวลาเชื่อมต่อบริการ AI (timeout) กรุณาลองใหม่ครับ"
    if isinstance(e, RateLimitError):
        return "❌ ตอนนี้มีการใช้งานหนาแน่น (rate limit) กรุณาลองใหม่ครับ"
    if isinstance(e, AuthenticationError):
        return "❌ API key ไม่ถูกต้องหรือหมดสิทธิ์ (ตรวจสอบ OPENAI_API_KEY)"
    if isinstance(e, (APIConnectionError, APIStatusError, BadRequestError, APIError)):
        # ไม่โชว์รายละเอียดดิบเกินไป
        return "❌ บริการ AI ขัดข้องชั่วคราว กรุณาลองใหม่ครับ"
    return f"❌ ข้อผิดพลาดไม่ทราบสาเหตุ: {e}"

# ========================
# Smart Model Picker
# ========================
HARD_KEYWORDS = [
    "วิเคราะห์เชิงลึก", "พิสูจน์", "ซับซ้อน", "โจทย์ยาก", "ออกแบบสถาปัตยกรรม",
    "เขียนโค้ด", "refactor", "optimize", "algorithm", "big-o", "regex",
    "ทดสอบหน่วย", "unit test", "sql", "schema", "กฎหมาย", "วางกลยุทธ์", "แผนธุรกิจ",
]

def pick_model(prompt: Optional[str] = None, force: Optional[str] = None) -> str:
    """เลือกโมเดลอัตโนมัติ: ดีฟอลต์ gpt-5-mini; ถ้ายาก/ยาว/มีโค้ด → gpt-5"""
    if force:
        return force
    if not prompt:
        return DEFAULT_MODEL
    text = (prompt or "").lower()
    hard = any(k in text for k in HARD_KEYWORDS)
    hard = hard or len(prompt) > 1200 or "```" in prompt or "select " in text or "create table" in text
    return STRONG_MODEL if hard else DEFAULT_MODEL

# ==========================
# System No-Echo Injection
# ==========================
def ensure_no_echo_system(
    messages: List[Dict[str, Any]],
    system_text: str = SYSTEM_NO_ECHO,
) -> List[Dict[str, Any]]:
    """
    บังคับให้มี system message แรกสุดเป็น SYSTEM_NO_ECHO
    - ถ้ามี system อื่น ๆ ใน messages จะตามหลัง no-echo
    """
    # แยก system เดิมออกมาก่อน (คงลำดับเดิม)
    systems = [m for m in messages if (m.get("role") == "system")]
    others  = [m for m in messages if (m.get("role") != "system")]
    out = [{"role": "system", "content": system_text}]
    out.extend(systems)
    out.extend(others)
    return out

def _coerce_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ทำความสะอาด structure เบื้องต้น: ตัดช่องว่าง, บังคับชนิด role/content เป็น string
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = str(m.get("role", "") or "").strip().lower()
        content = m.get("content", "")
        if not role or content is None:
            continue
        out.append({"role": role, "content": content if isinstance(content, (str, list, dict)) else str(content)})
    return out

# ==========================
# Core Chat Completions
# ==========================
def chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    *,
    no_echo: bool = False,
) -> str:
    """เรียก chat.completions แบบปกติ — คืนข้อความอย่างเดียว"""
    try:
        _messages = _coerce_messages(messages)
        if no_echo:
            _messages = ensure_no_echo_system(_messages)

        resp = client.chat.completions.create(
            model=(model or DEFAULT_MODEL),
            messages=_messages,
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
    *,
    no_echo: bool = False,
) -> str:
    """
    เลือกโมเดลอัตโนมัติ + fallback:
    - ปกติ: gpt-5-mini
    - ยาก/ยาว/มีโค้ด หรือ prefer_strong=True: gpt-5
    - ถ้า error จะสลับไปอีกโมเดลให้อัตโนมัติ
    """
    # หา user prompt ล่าสุดเพื่อพิจารณาความยาก
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = str(m.get("content") or "")
            break

    model = STRONG_MODEL if prefer_strong else pick_model(user_txt)
    try:
        _messages = _coerce_messages(messages)
        if no_echo:
            _messages = ensure_no_echo_system(_messages)

        resp = client.chat.completions.create(
            model=model,
            messages=_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        # fallback
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        try:
            _messages = _coerce_messages(messages)
            if no_echo:
                _messages = ensure_no_echo_system(_messages)
            resp = client.chat.completions.create(
                model=backup,
                messages=_messages,
                temperature=temperature,
                max_tokens=max_tokens,
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
    *,
    no_echo: bool = False,
) -> Any:
    """
    ใช้กับ Function Calling:
    - เลือกโมเดลอัตโนมัติ (หรือยกไป strong)
    - ส่งคืน response object (เพื่ออ่าน tool_calls เอง)
    - มี fallback สลับโมเดลฝั่งตรงข้ามให้
    """
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = str(m.get("content") or "")
            break

    model = STRONG_MODEL if prefer_strong else pick_model(user_txt)
    try:
        _messages = _coerce_messages(messages)
        if no_echo:
            _messages = ensure_no_echo_system(_messages)

        return client.chat.completions.create(
            model=model,
            messages=_messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception:
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        _messages = _coerce_messages(messages)
        if no_echo:
            _messages = ensure_no_echo_system(_messages)
        return client.chat.completions.create(
            model=backup,
            messages=_messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

def simple_ask(prompt: str, model: Optional[str] = None, *, no_echo: bool = True) -> str:
    """ยิงถามสั้น ๆ (role=user) — ค่าเริ่มต้น no_echo=True"""
    msgs = [
        {"role": "system", "content": "You are a helpful, concise assistant."},
        {"role": "user", "content": (prompt or "").strip()},
    ]
    return chat_completion_smart(msgs, no_echo=no_echo, prefer_strong=False, max_tokens=None) if not model \
        else chat_completion(msgs, model=model, no_echo=no_echo)

def chat_no_echo(
    user_text: str,
    *,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
) -> str:
    """
    ยิง user_text โดยแทรก System 'ไม่ทวนคำถาม' ให้อัตโนมัติ
    ใช้ใน handler ได้ทันที: reply = chat_no_echo(user_text)
    """
    messages = [
        {"role": "system", "content": SYSTEM_NO_ECHO},
        {"role": "user", "content": (user_text or "").strip()},
    ]
    return chat_completion_smart(
        messages,
        prefer_strong=False,
        temperature=temperature,
        max_tokens=max_tokens,
        no_echo=False,  # ใส่ SYSTEM_NO_ECHO เองแล้ว จึงไม่ต้อง enforce ซ้ำ
    ) if not model else chat_completion(messages, model=model, temperature=temperature, max_tokens=max_tokens, no_echo=False)

# ==================================
# Vision (URL/dataURL) + Image Gen
# ==================================
def vision_analyze(
    image_urls_or_dataurls: List[str],
    prompt: str = "Analyze this image in Thai, be concise.",
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    """
    วิเคราะห์ภาพด้วยโมเดล Vision
    - รองรับ URL หรือ dataURL ('data:image/png;base64,...')
    - หากต้องการส่งหลายภาพ ให้ส่งเป็นลิสต์
    """
    _model = (model or VISION_MODEL)
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    for u in (image_urls_or_dataurls or []):
        if not u:
            continue
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

def _bytes_to_data_url(img_bytes: bytes, mime: str = "image/png") -> str:
    """แปลง bytes → dataURL (ใช้กับ vision_analyze)"""
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def vision_analyze_bytes(
    images: List[bytes],
    prompt: str = "Analyze this image in Thai, be concise.",
    mime: str = "image/png",
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    """ส่งภาพแบบ bytes โดยไม่ต้องอัปโหลดที่ไหนก่อน"""
    urls = [_bytes_to_data_url(b, mime=mime) for b in images if b]
    return vision_analyze(urls, prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens)

def image_generate_file(
    prompt: str,
    size: str = "1024x1024",
    out_path: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[str]:
    """
    สร้างภาพด้วย gpt-image-1 แล้วบันทึกเป็นไฟล์ PNG
    คืน path ของไฟล์ หรือ None หากผิดพลาด
    """
    _model = (model or IMAGE_MODEL)
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

# ============================
# (ทางเลือก) Streaming Output
# ============================
def stream_chat(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    *,
    no_echo: bool = True,
) -> Iterable[str]:
    """
    สตรีมผลลัพธ์เป็นส่วน ๆ (generator ของข้อความ)
    หมายเหตุ: ใช้เมื่อคุณต้องการพิมพ์สดใน UI — ถ้าไม่จำเป็น ให้ใช้ chat_completion_smart ปกติ
    """
    _messages = _coerce_messages(messages)
    if no_echo:
        _messages = ensure_no_echo_system(_messages)
    _model = model or DEFAULT_MODEL
    try:
        stream = client.chat.completions.create(
            model=_model,
            messages=_messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                yield delta
    except Exception as e:
        yield _err_to_text(e)

__all__ = [
    "client",
    "SYSTEM_NO_ECHO",
    "pick_model",
    "ensure_no_echo_system",
    "chat_completion",
    "chat_completion_smart",
    "chat_with_tools_smart",
    "simple_ask",
    "chat_no_echo",
    "vision_analyze",
    "vision_analyze_bytes",
    "image_generate_file",
    "stream_chat",
]
