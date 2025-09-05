# utils/gemini_client.py
# -*- coding: utf-8 -*-
"""
Gemini Client (SDK v1) — hardened & feature-complete
- Smart model picker (Flash/Pro) + sensible timeouts
- Vision: analyze multiple images (bytes / file paths / PIL.Image)
- Image generation: try Imagen 3 models (imagen-3.0, imagen-3.0-fast, imagen-3.0-generate) with graceful fallback
- Robust error handling -> user-friendly Thai messages
- Optional web-aided answering (uses utils.google_search_utils if available)

ENV
  GEMINI_API_KEY                 (required)
  GEMINI_TIMEOUT_SEC             default 60
  GEMINI_IMAGE_GEN_TIMEOUT_SEC   default 120
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union, Iterable
import os
import io
import uuid

import google.generativeai as genai
from google.api_core import exceptions as gexc

try:
    from PIL import Image
except Exception:
    Image = None  # vision still works with bytes via SDK file upload path if PIL missing

# ---------- ENV & Config ----------
API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
TEXT_TIMEOUT = float(os.getenv("GEMINI_TIMEOUT_SEC", "60"))
IMAGE_GEN_TIMEOUT = float(os.getenv("GEMINI_IMAGE_GEN_TIMEOUT_SEC", "120"))

if not API_KEY:
    print("[gemini_client] ⚠️ GEMINI_API_KEY is not set")

# Configure once
try:
    if API_KEY:
        genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"[gemini_client] ❌ configure failed: {e}")

# ---------- Models (lazily resolved) ----------
_TEXT_MODELS = {
    "flash": "gemini-1.5-flash-latest",
    "pro":   "gemini-1.5-pro-latest",
}
_IMAGEN_CANDIDATES = [
    "imagen-3.0",
    "imagen-3.0-fast",
    "imagen-3.0-generate",
    # keep trying future aliases above if available
]

def _get_model(name: str):
    try:
        return genai.GenerativeModel(name)
    except Exception as e:
        print(f"[gemini_client] model init failed: {name}: {e}")
        return None

# Cache instances
_MODEL_FLASH = _get_model(_TEXT_MODELS["flash"]) if API_KEY else None
_MODEL_PRO   = _get_model(_TEXT_MODELS["pro"])   if API_KEY else None
_MODEL_IMAGEN = None
for m in _IMAGEN_CANDIDATES:
    _MODEL_IMAGEN = _get_model(m)
    if _MODEL_IMAGEN:
        break

# ---------- Helpers ----------
def _err_to_text(e: Exception) -> str:
    if isinstance(e, gexc.DeadlineExceeded):
        return "❌ หมดเวลาเชื่อมต่อบริการ Gemini (timeout)"
    if isinstance(e, (gexc.PermissionDenied, gexc.Unauthenticated)):
        return "❌ API key ของ Gemini ไม่ถูกต้องหรือหมดสิทธิ์ (ตรวจ GEMINI_API_KEY)"
    if isinstance(e, gexc.ResourceExhausted):
        return "❌ ใช้งานหนาแน่น (rate limit) กรุณาลองใหม่"
    if isinstance(e, gexc.InvalidArgument):
        return f"❌ คำขอที่ส่งให้ Gemini ไม่ถูกต้อง: {e}"
    if isinstance(e, gexc.NotFound):
        return f"❌ ไม่พบโมเดลที่เรียกใช้: {e}"
    return f"❌ ขัดข้องที่บริการ Gemini: {e}"

def _safe_text(resp) -> str:
    try:
        t = getattr(resp, "text", None)
        if t:
            return t.strip()
        # บางรุ่นตอบเป็น candidates
        cands = getattr(resp, "candidates", None)
        if cands:
            for c in cands:
                parts = getattr(getattr(c, "content", None), "parts", None)
                if parts:
                    for p in parts:
                        if getattr(p, "text", None):
                            return p.text.strip()
        return ""
    except Exception:
        return ""

def _choose_model(prefer_strong: bool, prompt: str) -> Any:
    """
    เลือก Flash/Pro อัตโนมัติ:
      - ถ้า prefer_strong=True หรือ prompt ยาวมาก/ซับซ้อน -> Pro
      - อื่น ๆ -> Flash (เร็ว/คุ้ม)
    """
    if prefer_strong or (prompt and len(prompt) > 3500):
        return _MODEL_PRO or _MODEL_FLASH
    return _MODEL_FLASH or _MODEL_PRO

def _bytes_from_image_like(x: Union[bytes, "Image.Image", str]) -> bytes:
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    if Image is not None and isinstance(x, Image.Image):
        buf = io.BytesIO()
        x.save(buf, format="PNG")
        return buf.getvalue()
    if isinstance(x, str) and os.path.exists(x):
        with open(x, "rb") as f:
            return f.read()
    raise ValueError("Unsupported image input; pass bytes, PIL.Image, or file path")

# ---------- Optional: Web-aided answering ----------
def _maybe_fetch_web_context(queries: Optional[List[str]], limit: int = 3) -> Optional[str]:
    """
    ถ้ามี utils.google_search_utils ให้ดึงสรุปเว็บมาผสาน
    คืนสตริงสรุปสั้น ๆ หรือ None
    """
    if not queries:
        return None
    try:
        from utils.google_search_utils import google_search  # optional dependency
    except Exception:
        return None

    try:
        chunks: List[str] = []
        for q in queries:
            res = google_search(q, num=limit, search_type="web", return_format="list")
            if isinstance(res, list):
                for it in res[:limit]:
                    t = it.get("title", "")
                    s = it.get("snippet", "")
                    l = it.get("link", "")
                    chunks.append(f"- {t}\n  {s}\n  {l}")
        return "Web context (top results):\n" + "\n".join(chunks) if chunks else None
    except Exception:
        return None

# ---------- Public APIs ----------
def generate_text(
    prompt: str,
    prefer_strong: bool = False,
    *,
    web_queries: Optional[List[str]] = None,
    system_instruction: Optional[str] = None,
) -> str:
    """
    สร้างข้อความตอบกลับจาก Gemini
    - เลือก Flash/Pro ให้โดยอัตโนมัติ (หรือบังคับด้วย prefer_strong=True)
    - ผสานสรุปจากเว็บ (ถ้าให้ web_queries และมี google_search_utils)
    - รองรับ system_instruction แบบเบา ๆ
    """
    if not (_MODEL_PRO or _MODEL_FLASH):
        return "❌ ไม่สามารถเริ่มต้นโมเดล Gemini ได้ (ตรวจ GEMINI_API_KEY)"

    model = _choose_model(prefer_strong, prompt)
    if not model:
        return "❌ ไม่พบโมเดลที่ใช้งานได้"

    # Compose final prompt
    ctx = _maybe_fetch_web_context(web_queries) if web_queries else None
    messages: List[Any] = []
    if system_instruction:
        messages.append(f"[System]\n{system_instruction}")
    if ctx:
        messages.append(f"[Context]\n{ctx}")
    messages.append(prompt)

    try:
        resp = model.generate_content(
            messages if len(messages) > 1 else prompt,
            request_options={"timeout": TEXT_TIMEOUT},
        )
        out = _safe_text(resp)
        if out:
            return out
        return "❌ ได้รับคำตอบว่างเปล่าจากโมเดล"
    except Exception as e:
        # Try backup model once
        backup = _MODEL_PRO if model is _MODEL_FLASH else _MODEL_FLASH
        if backup:
            try:
                resp = backup.generate_content(
                    messages if len(messages) > 1 else prompt,
                    request_options={"timeout": TEXT_TIMEOUT},
                )
                out = _safe_text(resp)
                if out:
                    return out
                return "❌ ได้รับคำตอบว่างเปล่าจากโมเดล (สำรอง)"
            except Exception as e2:
                return _err_to_text(e2)
        return _err_to_text(e)

def vision_analyze(
    images: Iterable[Union[bytes, "Image.Image", str]],
    prompt: str = "วิเคราะห์ภาพนี้และสรุปประเด็นสำคัญ",
    prefer_strong: bool = True,
) -> str:
    """
    วิเคราะห์ภาพหลายรูป (bytes / PIL.Image / file path)
    """
    model = _MODEL_PRO if prefer_strong and _MODEL_PRO else (_MODEL_PRO or _MODEL_FLASH)
    if not model:
        return "❌ ไม่สามารถเริ่มต้นโมเดลสำหรับวิเคราะห์ภาพได้"

    # Build multi-part content: [prompt, img1, img2, ...]
    parts: List[Any] = [prompt]
    try:
        for x in images:
            b = _bytes_from_image_like(x)
            if Image is not None:
                # Pass as PIL.Image (SDK รองรับ)
                im = Image.open(io.BytesIO(b))
                parts.append(im)
            else:
                # Fallback: upload bytes as file (slower but safe)
                upload = genai.upload_file(io.BytesIO(b), mime_type="image/png")
                parts.append(upload)
    except Exception as e:
        return f"❌ เตรียมไฟล์ภาพไม่สำเร็จ: {e}"

    try:
        resp = model.generate_content(
            parts,
            request_options={"timeout": TEXT_TIMEOUT},
        )
        out = _safe_text(resp)
        return out or "❌ โมเดลไม่ส่งคำบรรยายกลับมา"
    except Exception as e:
        return _err_to_text(e)

def generate_image_file(
    prompt: str,
    out_path: Optional[str] = None,
) -> Optional[str]:
    """
    สร้างภาพด้วย Imagen 3 (ถ้ามี) และบันทึกเป็น PNG
    คืน path ไฟล์ หรือสตริง error
    หมายเหตุ: ตระกูล Gemini 1.5 (text) ไม่ได้คืน 'ภาพ' จาก generate_content โดยตรง
    """
    if not _MODEL_IMAGEN:
        return "❌ ยังไม่พร้อมใช้งานการสร้างภาพ (ไม่พบรุ่น Imagen 3 ใน SDK)"

    # สร้างไฟล์ปลายทาง
    filename = out_path or f"generated_{uuid.uuid4().hex[:8]}.png"

    try:
        # SDK รุ่นใหม่มี .generate_images; เผื่อบางเวอร์ชันมีเฉพาะ generate_content
        gen_images = getattr(_MODEL_IMAGEN, "generate_images", None)
        if callable(gen_images):
            res = gen_images(
                prompt=prompt,
                request_options={"timeout": IMAGE_GEN_TIMEOUT},
            )
            imgs = getattr(res, "images", None) or []
            if not imgs:
                # บางเวอร์ชันเก็บ bytes ที่ res.image[0].bytes หรือ image.image_bytes
                for key in ("image", "image_bytes", "bytes"):
                    cand = getattr(res, key, None)
                    if cand:
                        imgs = [res]
                        break
            if not imgs:
                # ลองอ่านข้อความ error ถ้ามี
                msg = _safe_text(res) or "model returned no images"
                return f"❌ ไม่สามารถสร้างภาพได้: {msg}"
            # รับรูปแรกพอ
            img0 = imgs[0]
            # รองรับหลายรูปแบบ field
            data = getattr(img0, "image_bytes", None) or getattr(img0, "bytes", None)
            if data is None and hasattr(img0, "to_bytes"):
                data = img0.to_bytes()
            if data is None:
                # บางออบเจ็กต์เป็น PIL.Image แล้ว
                maybe_pil = img0 if Image and isinstance(img0, Image.Image) else None
                if maybe_pil:
                    maybe_pil.save(filename, "PNG")
                    return filename
                return "❌ SDK ไม่ได้คืน image bytes ที่เข้าถึงได้"
            with open(filename, "wb") as f:
                f.write(data)
            return filename

        # Fallback: บาง build รองรับผ่าน generate_content
        res = _MODEL_IMAGEN.generate_content(
            prompt,
            request_options={"timeout": IMAGE_GEN_TIMEOUT},
        )
        # พยายามเค้น bytes จาก parts
        parts = getattr(res, "parts", None) or []
        for p in parts:
            inline = getattr(p, "inline_data", None)
            if inline and getattr(inline, "data", None):
                with open(filename, "wb") as f:
                    f.write(inline.data)
                return filename
        msg = _safe_text(res) or "model returned no binary image data"
        return f"❌ ไม่สามารถสร้างภาพได้: {msg}"

    except Exception as e:
        return _err_to_text(e)

def simple_ask(prompt: str) -> str:
    """ยิงคำถามสั้น ๆ ไปยังโมเดล Flash เพื่อคำตอบไว"""
    return generate_text(prompt, prefer_strong=False)
