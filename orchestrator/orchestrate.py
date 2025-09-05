# providers/gemini_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import time

from config import GOOGLE_API_KEY, GEMINI_MODEL_DIALOGUE

def _to_gemini_history(messages: List[Dict[str, str]]):
    """แปลง messages เป็นโครงสร้างที่ Gemini คุ้น"""
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            role = "model"
        content = (m.get("content") or "").strip()
        if not content:
            continue
        out.append({"role": role, "parts": [content]})
    return out

_SYSTEM_PROMPT = (
    "คุณคือ 'ชิบะน้อย' ผู้ช่วยภาษาไทยที่สุภาพ กระชับ ไม่ทวนคำถาม และซื่อสัตย์ "
    "หากข้อมูลไม่แน่ใจให้บอกตรง ๆ และเสนอแนวทางค้นเพิ่มเติม"
)

def call_gemini(
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_output_tokens: int = 1024,
) -> str:
    """
    เรียก Google Generative AI (google-generativeai>=0.8.x)
    ใช้คีย์/โมเดลจาก config.py
    - ถ้าคีย์หายหรือเกิดข้อผิดพลาด → raise เพื่อให้ orchestrator ทำ fallback
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    import google.generativeai as genai  # type: ignore
    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(
        GEMINI_MODEL_DIALOGUE or "gemini-1.5-pro",
        system_instruction=_SYSTEM_PROMPT,
    )

    if not messages:
        return ""

    history = _to_gemini_history(messages[:-1])
    prompt = (messages[-1].get("content") or "").strip()

    gen_cfg = {
        "temperature": float(temperature),
        "max_output_tokens": int(max_output_tokens),
    }

    # retry เบา ๆ กรณี rate limit/เน็ตแกว่ง
    last_err = None
    for attempt in range(2):  # 2 ครั้งก็พอ เบา ๆ
        try:
            chat = model.start_chat(history=history)
            rsp = chat.send_message(prompt, generation_config=gen_cfg)
            text = (getattr(rsp, "text", "") or "").strip()
            return text
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if attempt == 0 and ("429" in msg or "rate" in msg or "exhausted" in msg or "deadline" in msg):
                time.sleep(0.8)
                continue
            break

    # โยนออกให้ orchestrator ตัดสินใจ fallback
    raise RuntimeError(f"gemini_call_failed: {last_err}")
