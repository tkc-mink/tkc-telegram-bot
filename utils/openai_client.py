# utils/openai_client.py
# -*- coding: utf-8 -*-
"""
OpenAI client (SDK v1.x) แบบเสถียร + Smart Model Picker + No-Echo Mode

สิ่งที่เพิ่มจากเวอร์ชันเดิม:
- รองรับ "ไม่ทวนคำถาม" (No-Echo) โดยแทรก SYSTEM_NO_ECHO อัตโนมัติ
- เพิ่มฟังก์ชัน chat_no_echo(user_text, ...) สำหรับยิงเร็วแบบไม่ทวน
- เพิ่ม ensure_no_echo_system(messages, ...) เพื่อบังคับ System Prompt ในทุกเมธอดที่ใช้ messages
- ทุกเมธอดหลัก (chat_completion/chat_completion_smart/chat_with_tools_smart/simple_ask)
  รองรับพารามิเตอร์ no_echo: bool = False

ข้อดี:
- ไม่ต้องไปใส่ prefix "รับทราบ:" หรือ "คุณถามว่า" ที่อื่น
- ควบคุมพฤติกรรมไม่ทวนได้จากจุดกลาง

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
from typing import List, Dict, Any, Optional

from openai import OpenAI
from openai import APIError, RateLimitError, APITimeoutError, AuthenticationError

# ===== PROMPT TEMPLATES (ต้องมีไฟล์นี้ตามที่เตรียมไว้) =====
try:
    from utils.prompt_templates import SYSTEM_NO_ECHO
except Exception:
    # fallback ป้องกันกรณีไฟล์ยังไม่พร้อม
    SYSTEM_NO_ECHO = (
        "คุณเป็นผู้ช่วยที่ตอบสั้น กระชับ และตรงคำถาม "
        "ห้ามทวนคำถามหรือคัดลอกข้อความของผู้ใช้กลับมาก่อนตอบ "
        "ตอบทันทีเป็นประเด็น ไม่ต้องขึ้นต้นด้วยคำว่า 'รับทราบ' หรือ 'คุณถามว่า' "
        "หลีกเลี่ยงประโยคฟุ่มเฟือย และเน้นตอบเนื้อหาหลักเท่านั้น"
    )

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
    hard = hard or len(prompt) > 1200 or "```" in prompt or "select " in text or "create table" in text
    return STRONG_MODEL if hard else DEFAULT_MODEL


# ===== Utilities: enforce No-Echo System Prompt =====
def ensure_no_echo_system(
    messages: List[Dict[str, Any]],
    system_text: str = SYSTEM_NO_ECHO,
    force_insert_first: bool = True
) -> List[Dict[str, Any]]:
    """
    แทรกหรือแทนที่ system message เป็น SYSTEM_NO_ECHO
    - ถ้า force_insert_first=True: บังคับให้ system อยู่ index 0 เสมอ
    - ถ้ามี system เดิมอยู่แล้ว จะคงไว้เป็นรายการถัดไป (ป้องกันการทำลาย instruction อื่น)
    """
    msgs = []
    found_system = False
    for m in messages:
        if m.get("role") == "system":
            found_system = True
            # ข้ามไปก่อน เพื่อจัดตำแหน่งใหม่
            continue
        msgs.append(m)

    # ใส่ system_no_echo เป็นอันแรก
    out = [{"role": "system", "content": system_text}]
    if found_system:
        # นำ system เดิมทุกอัน (ถ้าต้องการ) มาต่อท้าย system_no_echo
        for m in messages:
            if m.get("role") == "system":
                out.append(m)
        out.extend([m for m in msgs if m.get("role") != "system"])
        return out

    # ไม่มี system เดิม ก็แค่ใส่ที่หัว
    out.extend(msgs)
    return out


# ===== Chat (ข้อความอย่างเดียว) =====
def chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    *,
    no_echo: bool = False
) -> str:
    """เรียก chat.completions และคืนเฉพาะข้อความตอบกลับ"""
    _model = model or DEFAULT_MODEL
    try:
        _messages = messages
        if no_echo:
            _messages = ensure_no_echo_system(messages)

        resp = client.chat.completions.create(
            model=_model,
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
    no_echo: bool = False
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
        _messages = messages
        if no_echo:
            _messages = ensure_no_echo_system(messages)

        resp = client.chat.completions.create(
            model=model, messages=_messages, temperature=temperature, max_tokens=max_tokens
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        # ลองอีกโมเดลหนึ่งเป็นสำรอง
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        try:
            _messages = messages
            if no_echo:
                _messages = ensure_no_echo_system(messages)

            resp = client.chat.completions.create(
                model=backup, messages=_messages, temperature=temperature, max_tokens=max_tokens
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
    no_echo: bool = False
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
        _messages = messages
        if no_echo:
            _messages = ensure_no_echo_system(messages)

        return client.chat.completions.create(
            model=model, messages=_messages, tools=tools,
            tool_choice=tool_choice, temperature=temperature, max_tokens=max_tokens
        )
    except Exception:
        backup = DEFAULT_MODEL if model == STRONG_MODEL else STRONG_MODEL
        return client.chat.completions.create(
            model=backup, messages=_messages if not no_echo else ensure_no_echo_system(messages),
            tools=tools, tool_choice=tool_choice, temperature=temperature, max_tokens=max_tokens
        )


def simple_ask(prompt: str, model: Optional[str] = None, *, no_echo: bool = True) -> str:
    """ถามสั้น ๆ (role=user) — ค่าเริ่มต้น no_echo=True เพื่อกันนิสัยทวนโดยไม่ต้องใส่เพิ่ม"""
    msgs = [
        # system จะถูกแทนด้วย SYSTEM_NO_ECHO เมื่อ no_echo=True
        {"role": "system", "content": "You are a helpful, concise assistant."},
        {"role": "user", "content": prompt},
    ]
    if model:
        return chat_completion(msgs, model=model, no_echo=no_echo)
    return chat_completion_smart(msgs, no_echo=no_echo)


# ===== ทางลัด: ไม่ทวนคำถามด้วย user_text ตรง ๆ =====
def chat_no_echo(user_text: str, *, model: Optional[str] = None, temperature: float = 0.3, max_tokens: Optional[int] = None) -> str:
    """
    ยิงข้อความผู้ใช้ตรง ๆ ด้วย System 'ห้ามทวนคำถาม'
    ใช้งานใน handler ได้ทันที เช่น:
        answer = chat_no_echo(user_text)
    """
    messages = [
        {"role": "system", "content": SYSTEM_NO_ECHO},
        {"role": "user", "content": (user_text or "").strip()},
    ]
    return chat_completion_smart(messages, prefer_strong=False, temperature=temperature, max_tokens=max_tokens, no_echo=False)


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
