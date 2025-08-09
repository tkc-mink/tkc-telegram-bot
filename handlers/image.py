# handlers/image.py
# -*- coding: utf-8 -*-
"""
รองรับ 2 โหมด:
1) วิเคราะห์ภาพ (Vision): ผู้ใช้ส่งรูปภาพ + (แคปชันเสริมได้)
2) สร้างภาพ (Image Gen): คำสั่ง /imagine <prompt>
"""

import os
import base64
from typing import Optional

from utils.message_utils import send_message, send_photo
from utils.telegram_file_utils import download_telegram_file  # ต้องมีอยู่แล้วในโปรเจกต์
from utils.openai_client import client  # ใช้ client กลาง (ห้ามใช้ proxies)
# ENV ตั้งชื่อโมเดลผ่าน OPENAI_MODEL_VISION / OPENAI_MODEL_IMAGE ได้
VISION_MODEL = os.getenv("OPENAI_MODEL_VISION", "gpt-4o-mini")
IMAGE_MODEL  = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1")


def _file_to_data_url(path: str) -> str:
    """แปลงไฟล์รูปเป็น data URL (base64) สำหรับ vision"""
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
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
    """สร้างภาพด้วย gpt-image-1 แล้วคืน bytes (PNG/JPEG)"""
    p = prompt.strip() or "a cute shiba inu 3d sticker, thai text 'ชิบะน้อย'"
    resp = client.images.generate(
        model=IMAGE_MODEL,
        prompt=p,
        size=os.getenv("OPENAI_IMAGE_SIZE", "1024x1024"),
    )
    # SDK v1 จะให้ base64 กลับมาใน data[0].b64_json
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)


def handle_image(chat_id: int, msg: dict) -> None:
    """
    เคสที่รองรับ:
    - ผู้ใช้ส่งรูป -> วิเคราะห์รูป (ใช้ caption เป็นคำสั่งได้)
    - ผู้ใช้พิมพ์ /imagine <prompt> -> สร้างภาพใหม่
    """
    try:
        text = (msg.get("caption") or msg.get("text") or "").strip()

        # โหมดสร้างภาพเมื่อพิมพ์ /imagine
        if text.lower().startswith("/imagine"):
            prompt = text.replace("/imagine", "", 1).strip()
            if not prompt:
                send_message(chat_id, "พิมพ์ /imagine ตามด้วยคำอธิบายภาพที่ต้องการ เช่น /imagine ชิบะใส่หมวกเชฟ")
                return

            img_bytes = _generate_image(prompt)
            send_photo(chat_id, img_bytes, caption=f"🎨 สร้างจากคำสั่ง: {prompt}")
            return

        # โหมดวิเคราะห์รูป (ผู้ใช้ส่งรูปมา)
        if msg.get("photo"):
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
                send_message(chat_id, f"🖼️ ผลวิเคราะห์ภาพ:\n{result}")
            finally:
                try:
                    os.remove(local_path)
                except Exception:
                    pass
            return

        # ถ้าไม่ได้ส่งรูป และไม่ได้ /imagine
        send_message(chat_id, "ส่งรูปมาให้ดู หรือใช้คำสั่ง /imagine <prompt> เพื่อให้ผมสร้างภาพครับ")

    except Exception as e:
        send_message(chat_id, f"❌ จัดการรูปภาพไม่สำเร็จ: {e}")
