# utils/gemini_client.py
# -*- coding: utf-8 -*-
"""
Gemini client with Real-time Search & Smart Model Picker.
This client connects to the Gemini API and leverages its built-in
real-time search capabilities.

ENV:
  GEMINI_API_KEY          (จำเป็น)
  GEMINI_TIMEOUT_SEC      ดีฟอลต์ 60
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

# ===== ENV =====
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SEC", "60"))

if not API_KEY:
    print("[gemini_client] WARNING: GEMINI_API_KEY is not set")

# ===== Configure Gemini Client =====
genai.configure(api_key=API_KEY)

# ===== Model Definitions =====
# เราสามารถใช้ Pro สำหรับทุกอย่าง หรือจะแยก Flash สำหรับงานเร็วก็ได้
MODEL_PRO = genai.GenerativeModel('gemini-1.5-pro-latest')
MODEL_FLASH = genai.GenerativeModel('gemini-1.5-flash-latest')

# ===== Error Helper =====
def _err_to_text(e: Exception) -> str:
    if isinstance(e, (google_exceptions.DeadlineExceeded, )):
        return "❌ หมดเวลาเชื่อมต่อบริการ Gemini กรุณาลองใหม่อีกครั้ง (timeout)"
    if isinstance(e, (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated)):
        return "❌ API key ของ Gemini ไม่ถูกต้องหรือหมดสิทธิ์ กรุณาตรวจสอบค่า GEMINI_API_KEY"
    if isinstance(e, (google_exceptions.ResourceExhausted, )):
        return "❌ มีการใช้งาน Gemini หนาแน่น (rate limit) กรุณาลองใหม่อีกครั้งครับ"
    return f"❌ ข้อผิดพลาดจาก Gemini: {e}"

# ===== Core Functions =====
def generate_text(prompt: str, prefer_strong: bool = False) -> str:
    """
    สร้างข้อความตอบกลับจาก Gemini พร้อมความสามารถในการค้นหาข้อมูลแบบเรียลไทม์
    - ถ้า prefer_strong=True จะใช้โมเดล Pro, มิฉะนั้นใช้ Flash
    """
    model_to_use = MODEL_PRO if prefer_strong else MODEL_FLASH
    try:
        # Gemini API รับแค่ข้อความตรงๆ ไม่ต้องสร้าง message list ที่ซับซ้อน
        response = model_to_use.generate_content(
            prompt,
            request_options={"timeout": TIMEOUT}
        )
        return response.text.strip()
    except Exception as e:
        # ลองสลับโมเดลสำรอง (เหมือนโค้ดเดิมของคุณ)
        backup_model = MODEL_PRO if model_to_use == MODEL_FLASH else MODEL_FLASH
        try:
            response = backup_model.generate_content(
                prompt,
                request_options={"timeout": TIMEOUT}
            )
            return response.text.strip()
        except Exception as e2:
            return _err_to_text(e2)

# --- คุณสามารถเพิ่มฟังก์ชัน vision_analyze และ image_generate_file ที่นี่ได้ในภายหลัง ---

# ===== ทางลัดสำหรับถามสั้นๆ (เหมือน simple_ask) =====
def simple_ask(prompt: str) -> str:
    """
    ยิงคำถามสั้นๆ ไปยังโมเดล Flash เพื่อการตอบสนองที่รวดเร็ว
    """
    return generate_text(prompt, prefer_strong=False)
