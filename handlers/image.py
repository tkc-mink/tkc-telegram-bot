# handlers/image.py
# -*- coding: utf-8 -*-
"""
รองรับ 2 โหมดหลัก:
1) วิเคราะห์ภาพ (Vision): ผู้ใช้ส่งรูปภาพ + (แคปชันเสริมได้)
2) สร้างภาพ (Image Gen): คำสั่ง /imagine <prompt>

หมายเหตุ:
- การส่งรูปกลับไป Telegram ด้วยไบต์ ต้องใช้ multipart/form-data
- ใช้ get_telegram_token() เพื่ออัปโหลดไฟล์โดยตรง
"""

from __future__ import annotations
import os
import base64
import requests
from typing import Optional

from utils.message_utils import send_message, send_photo, get_telegram_token
from utils.telegram_file_utils import download_telegram_file
from utils.openai_client import client  # client กลาง (no proxies)
from utils.telegram_api import send_chat_action

# ENV ตั้งชื่อโมเดลผ่าน OPENAI_MODEL_VISION / OPENAI_MODEL_IMAGE ได้
VISION_MODEL = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
IMAGE_MODEL  = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1")
IMAGE_SIZE   = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")


# ---------- helpers ----------
def _file_to_data_url(path: str) -> str:
    """แปลงไฟล์รูปเป็น data URL (base64) สำหรับ vision"""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    # เดา mime แบบง่าย ๆ (ส่วนใหญ่เป็น jpeg จาก Telegram)
    return f"data:image/jpeg;base64,{b64}"


def _analyze_photo(caption: Optional[str], image_path: str) -> str:
    """เรียก Vision model วิเคราะห์ภาพ"""
    user_text = (caption or "อธิบายรูปนี้เป็นภาษาไทยแบบสั้นๆ").strip()
    data_url = _file_to_data_url(image_path)

    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": "คุณเป็นผู้ช่วยภาษาไทย อธิบายภาพอย่างสุภาพ กระชับ"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def _generate_image(prompt: str) -> bytes:
    """สร้างภาพด้วย gpt-image-1 แล้วคืน bytes (PNG)"""
    p = prompt.strip() or "a cute shiba inu 3d sticker, thai text 'ชิบะน้อย'"
    resp = client.images.generate(model=IMAGE_MODEL, prompt=p, size=IMAGE_SIZE)
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)


def _send_photo_bytes(chat_id: int, img_bytes: bytes, caption: Optional[str] = None) -> None:
    """
    ส่งรูปไป Telegram โดยอัปโหลดไบต์ (multipart/form-data)
    ใช้เมื่อเราได้รูปมาจากการ generate (ไม่มี URL/file_id)
    """
    token = get_telegram_token()
    if not token:
        print("[image] WARNING: no Telegram token set")
        send_message(chat_id, "❌ ระบบส่งรูปไม่สำเร็จ (token หาย)")
        return

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    files = {
        "photo": ("image.png", img_bytes, "image/png"),
    }
    data = {
        "chat_id": str(chat_id),
    }
    if caption:
        # ไม่ใส่ parse_mode เพื่อลดโอกาส 400 (can't parse entities)
        data["caption"] = caption[:1024]

    try:
        r = requests.post(url, data=data, files=files, timeout=60)
        if not r.ok:
            print("[image] sendPhoto multipart error:", r.status_code, r.text[:200])
            send_message(chat_id, "❌ ระบบส่งรูปไม่สำเร็จ (upload ผิดพลาด)")
    except Exception as e:
        print("[image] sendPhoto multipart exception:", e)
        send_message(chat_id, f"❌ ระบบส่งรูปไม่สำเร็จ: {e}")


# ---------- main entry ----------
def handle_image(chat_id: int, msg: dict) -> None:
    """
    เคสที่รองรับ:
    - ผู้ใช้ส่งรูป -> วิเคราะห์รูป (ใช้ caption เป็นคำสั่งได้)
    - ผู้ใช้พิมพ์ /imagine <prompt> -> สร้างภาพใหม่
    - กรณีสื่ออื่น ๆ (sticker/video/animation) จะตอบแนะแนวทาง
    """
    try:
        text = (msg.get("caption") or msg.get("text") or "").strip()
        low = text.lower()

        # ===== โหมดสร้างภาพ =====
        if low.startswith("/imagine"):
            prompt = text[8:].strip()  # ตัดคำสั่ง /imagine ออก
            if not prompt:
                send_message(chat_id, "พิมพ์ /imagine ตามด้วยคำอธิบายภาพที่ต้องการ เช่น\n/imagine ชิบะใส่หมวกเชฟ กำลังทำข้าวผัด")
                return

            # แสดงกำลังทำงาน
            try:
                send_chat_action(chat_id, "upload_photo")
            except Exception:
                pass

            try:
                img_bytes = _generate_image(prompt)
            except Exception as e:
                send_message(chat_id, f"❌ สร้างภาพไม่สำเร็จ: {e}")
                return

            _send_photo_bytes(chat_id, img_bytes, caption=f"🎨 สร้างจากคำสั่ง: {prompt}")
            return

        # ===== โหมดวิเคราะห์รูป =====
        if msg.get("photo"):
            # แจ้งกำลังพิมพ์/ประมวลผล
            try:
                send_chat_action(chat_id, "typing")
            except Exception:
                pass

            # เลือกไฟล์รูปที่ใหญ่สุดจาก array
            sizes = msg["photo"]
            best = max(sizes, key=lambda x: x.get("file_size", 0))
            file_id = best.get("file_id")
            if not file_id:
                send_message(chat_id, "❌ ไม่พบรูปภาพจาก Telegram")
                return

            local_path = download_telegram_file(file_id, "photo.jpg")
            if not local_path:
                send_message(chat_id, "❌ ดาวน์โหลดรูปไม่สำเร็จ")
                return

            try:
                result = _analyze_photo(text, local_path)
                # จำกัดความยาวคำตอบ (กันยาวเกิน)
                result = (result or "").strip()
                if len(result) > 3800:
                    result = result[:3800] + "…"
                send_message(chat_id, f"🖼️ ผลวิเคราะห์ภาพ:\n{result}")
            except Exception as e:
                send_message(chat_id, f"❌ วิเคราะห์รูปไม่สำเร็จ: {e}")
            finally:
                try:
                    os.remove(local_path)
                except Exception:
                    pass
            return

        # ===== สื่ออื่น ๆ ที่ main_handler ส่งมาตรงนี้ =====
        if msg.get("sticker"):
            send_message(chat_id, "สติ๊กเกอร์น่ารักมาก! ถ้าอยากให้ผมวิเคราะห์ภาพ ให้ส่ง ‘รูปภาพ’ หรือใช้คำสั่ง /imagine เพื่อสร้างภาพใหม่ครับ")
            return
        if msg.get("video") or msg.get("animation"):
            send_message(chat_id, "ตอนนี้ยังรองรับเฉพาะ ‘รูปภาพ’ สำหรับวิเคราะห์/สร้างภาพครับ 🙏")
            return

        # ไม่มีรูปและไม่ได้ /imagine
        send_message(chat_id, "ส่ง ‘รูปภาพ’ มาเพื่อให้ผมวิเคราะห์ หรือใช้คำสั่ง /imagine <prompt> เพื่อให้ผมสร้างภาพครับ")

    except Exception as e:
        send_message(chat_id, f"❌ จัดการรูปภาพไม่สำเร็จ: {e}")
