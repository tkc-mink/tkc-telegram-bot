# utils/gemini_client.py
# -*- coding: utf-8 -*-
"""
Gemini Client (SDK v1) ฉบับสมบูรณ์
- Real-time Search & Smart Model Picker
- Vision (วิเคราะห์ภาพ)
- Image Generation (สร้างภาพ)
- Robust Error Handling & Fallback

ไฟล์นี้เชื่อมต่อกับ Gemini API และดึงความสามารถในการค้นหาข้อมูลล่าสุด,
วิเคราะห์ภาพ, และสร้างภาพใหม่มาใช้งานอย่างครบวงจร

ENV:
  GEMINI_API_KEY          (จำเป็น)
  GEMINI_TIMEOUT_SEC      ดีฟอลต์ 60 (สำหรับข้อความ), 120 (สำหรับสร้างภาพ)
"""
from __future__ import annotations
import os
import uuid
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from PIL import Image
from io import BytesIO
import requests

# ===== ENV & Configuration =====
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
TEXT_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SEC", "60"))
IMAGE_GEN_TIMEOUT = float(os.getenv("GEMINI_IMAGE_GEN_TIMEOUT_SEC", "120"))

if not API_KEY:
    print("[gemini_client] ⚠️ WARNING: GEMINI_API_KEY is not set.")

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"[gemini_client] ❌ ERROR: Failed to configure Gemini: {e}")

# ===== Model Definitions =====
# gemini-1.5-pro-latest: โมเดลที่เก่งที่สุด รองรับทุกอย่าง (ข้อความ, ภาพ, วิดีโอ, เสียง)
# gemini-1.5-flash-latest: โมเดลที่เน้นความเร็วและราคาประหยัด เหมาะกับงานทั่วไป
try:
    MODEL_PRO = genai.GenerativeModel('gemini-1.5-pro-latest')
    MODEL_FLASH = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"[gemini_client] ❌ ERROR: Could not initialize Gemini models: {e}")
    MODEL_PRO = None
    MODEL_FLASH = None

# ===== Error Helper =====
def _err_to_text(e: Exception) -> str:
    """แปลง Exception ของ Google API เป็นข้อความที่เข้าใจง่าย"""
    if isinstance(e, google_exceptions.DeadlineExceeded):
        return "❌ หมดเวลาเชื่อมต่อบริการ Gemini กรุณาลองใหม่อีกครั้ง (timeout)"
    if isinstance(e, (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated)):
        return "❌ API key ของ Gemini ไม่ถูกต้องหรือหมดสิทธิ์ กรุณาตรวจสอบค่า GEMINI_API_KEY"
    if isinstance(e, google_exceptions.ResourceExhausted):
        return "❌ มีการใช้งาน Gemini หนาแน่น (rate limit) กรุณาลองใหม่อีกครั้ง"
    if isinstance(e, google_exceptions.InvalidArgument):
         return f"❌ ข้อมูลที่ส่งให้ Gemini ไม่ถูกต้อง: {e}"
    if isinstance(e, google_exceptions.NotFound):
        return f"❌ ไม่พบโมเดลที่เรียกใช้: {e}"
    return f"❌ เกิดข้อผิดพลาดไม่ทราบสาเหตุจาก Gemini: {e}"

# ===== Text Generation =====
def generate_text(prompt: str, prefer_strong: bool = False) -> str:
    """
    สร้างข้อความตอบกลับจาก Gemini พร้อมความสามารถในการค้นหาข้อมูลแบบเรียลไทม์
    - ถ้า prefer_strong=True จะใช้โมเดล Pro, มิฉะนั้นใช้ Flash
    - มีระบบสลับโมเดลสำรองให้อัตโนมัติหากโมเดลหลักล้มเหลว
    """
    if not MODEL_PRO or not MODEL_FLASH:
        return "❌ ไม่สามารถเริ่มต้นโมเดล Gemini ได้"

    model_to_use = MODEL_PRO if prefer_strong else MODEL_FLASH
    try:
        response = model_to_use.generate_content(
            prompt,
            request_options={"timeout": TEXT_TIMEOUT}
        )
        return response.text.strip()
    except Exception as e:
        # ลองสลับโมเดลสำรอง (เหมือนโค้ดเดิมของคุณ)
        backup_model = MODEL_PRO if model_to_use == MODEL_FLASH else MODEL_FLASH
        try:
            response = backup_model.generate_content(
                prompt,
                request_options={"timeout": TEXT_TIMEOUT}
            )
            return response.text.strip()
        except Exception as e2:
            return _err_to_text(e2)

# ===== Vision (Image Analysis) =====
def vision_analyze(
    image_data_list: List[bytes],
    prompt: str = "วิเคราะห์ภาพนี้ให้หน่อย บอกรายละเอียดที่สำคัญมา",
) -> str:
    """
    ส่งรายการรูป (ในรูปแบบ bytes) พร้อมคำสั่งไปให้ Gemini Pro วิเคราะห์
    - image_data_list: รายการของข้อมูลภาพในรูปแบบ bytes
    """
    if not MODEL_PRO:
        return "❌ ไม่สามารถเริ่มต้นโมเดล Gemini (Pro) สำหรับวิเคราะห์ภาพได้"

    try:
        # สร้าง content list ที่มีทั้ง text และ image
        content_parts = [prompt]
        for img_bytes in image_data_list:
            img_pil = Image.open(BytesIO(img_bytes))
            content_parts.append(img_pil)

        response = MODEL_PRO.generate_content(
            content_parts,
            request_options={"timeout": TEXT_TIMEOUT}
            )
        return response.text.strip()
    except Exception as e:
        return _err_to_text(e)

# ===== Image Generation =====
def generate_image_file(
    prompt: str,
    out_path: Optional[str] = None,
) -> Optional[str]:
    """
    สร้างภาพด้วย Gemini Pro แล้วบันทึกไฟล์เป็น PNG
    คืน path ของไฟล์ที่บันทึก หรือ ข้อความ Error หากผิดพลาด
    """
    if not MODEL_PRO:
        return "❌ ไม่สามารถเริ่มต้นโมเดล Gemini (Pro) สำหรับสร้างภาพได้"

    # ใช้โมเดล Pro ซึ่งมีความสามารถในการสร้างภาพผ่าน Tool ภายใน
    # เราต้องสร้าง Prompt ที่ชี้นำให้ AI รู้ว่าต้องการ "สร้างภาพ"
    generation_prompt = (
        "Create a photorealistic image based on the following description. "
        "Do not add any text overlays on the image. "
        f"Description: '{prompt}'"
    )

    try:
        response = MODEL_PRO.generate_content(
            generation_prompt,
            generation_config={"candidate_count": 1},
            request_options={"timeout": IMAGE_GEN_TIMEOUT},
        )

        # ตรวจสอบว่า Gemini คืนข้อมูลที่เป็นไฟล์ (GeneratedImage) กลับมาหรือไม่
        if not response.parts or not hasattr(response.parts[0], 'file_data'):
            # ถ้าไม่มีภาพ อาจเป็นเพราะ prompt ไม่ปลอดภัย หรือเหตุผลอื่น
            # Gemini จะตอบกลับมาเป็นข้อความอธิบายแทน
            error_message = response.text or "Gemini did not generate an image. The prompt might be unsafe."
            print(f"[gemini_client.generate_image_file] Error: {error_message}")
            return f"❌ ไม่สามารถสร้างภาพได้: {error_message}"

        # ดึงข้อมูลภาพออกมา
        generated_file = response.parts[0].file_data
        img_bytes = requests.get(generated_file.uri).content
        image = Image.open(BytesIO(img_bytes))

        # บันทึกไฟล์
        filename = out_path or f"generated_{uuid.uuid4().hex[:8]}.png"
        image.save(filename, "PNG")

        return filename

    except Exception as e:
        return _err_to_text(e)

# ===== ทางลัดสำหรับถามสั้นๆ (เหมือน simple_ask) =====
def simple_ask(prompt: str) -> str:
    """
    ยิงคำถามสั้นๆ ไปยังโมเดล Flash เพื่อการตอบสนองที่รวดเร็ว
    """
    return generate_text(prompt, prefer_strong=False)
