# providers/gemini_client.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
import os

def _to_gemini_history(messages: List[Dict[str, str]]):
    # แปลงเล็กน้อย: Gemini ใช้ [{"role":"user","parts":[...]}]
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            role = "model"
        if not m.get("content"):
            continue
        out.append({"role": role, "parts": [m["content"]]})
    return out

def call_gemini(messages: List[Dict[str, str]]) -> str:
    """
    เรียก Google Generative AI (google-generativeai>=0.8.x)
    ENV:
      GOOGLE_API_KEY
      GEMINI_MODEL_DIALOGUE (default: gemini-1.5-pro)
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return "ยังไม่ได้ตั้งค่า GOOGLE_API_KEY ครับ"

    import google.generativeai as genai  # type: ignore
    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL_DIALOGUE", "gemini-1.5-pro")
    model = genai.GenerativeModel(model_name)

    history = _to_gemini_history(messages[:-1])
    prompt = messages[-1]["content"]

    try:
        chat = model.start_chat(history=history)
        rsp = chat.send_message(prompt)
        return (getattr(rsp, "text", "") or "").strip()
    except Exception as e:
        raise
