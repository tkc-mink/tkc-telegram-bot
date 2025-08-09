# handlers/image.py
# -*- coding: utf-8 -*-
"""
รองรับ 2 โหมด:
1) ผู้ใช้ส่ง "รูปภาพ" มาให้บอท -> วิเคราะห์/อธิบายรูป (Vision)
2) ผู้ใช้พิมพ์ข้อความสั่งสร้างภาพ เช่น /imagine ภาพหมาชิบะนั่งยิ้ม -> สร้างรูปด้วย gpt-image-1

ต้องพึ่ง:
- utils.telegram_file_utils.download_telegram_file(file_id, file_name)  -> คืน path ไฟล์ชั่วคราว
- utils.message_utils.send_message(chat_id, text)
- utils.message_utils.send_photo(chat_id, image_path, caption=None)     -> ถ้ามี
"""

import os
import io
import base64
import mimetypes
from typing import Optional

from openai import OpenAI

from utils.message_utils import send_message
try:
    # เผื่อมีฟังก์ชันส่งรูปในโปรเจกต์
    from utils.message_utils import send_photo  # type: ignore
except Exception:
    send_photo = None  # ถ้าไม่มี จะ fallback เป็นส่งข้อความแทน

from utils.telegram_file_utils import download_telegram_file

# ---------- OpenAI Client ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")  # vision OK
IMAGE_MODEL  = os.getenv("OPENAI_IMAGE_MODEL",  "gpt-image-1")   # image gen


# ---------- Helpers ----------
def _file_to_data_url(path: str) -> str:
    """
    แปลงไฟล์ภาพเป็น data URL (base64) สำหรับส่งให้โมเดล Vision
    """
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        # เดาเป็น jpg ถ้าเดาไม่ได้
        mime = "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _analyze_image_with_gpt(image_path: str, user_hint: Optional[str] = None) -> str:
    """
    วิเคราะห์รูปด้วย Chat Completions (Vision)
    :param image_path: path ไฟล์ภาพบนเครื่อง
    :param user_hint: ข้อความช่วยอธิบายว่าต้องการให้วิเคราะห์ด้านใด
    """
    try:
        data_url = _file_to_data_url(image_path)
        user_text = user_hint.strip() if user_hint else "ช่วยอธิบายภาพนี้แบบสั้น กระชับ และสุภาพเป็นภาษาไทย"

        messages = [
            {
                "role": "system",
                "content": "คุณคือผู้ช่วยภาษาไทย สุภาพ กระชับ และตรงประเด็น",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]

        resp = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip() or "ขออภัย ไม่สามารถวิเคราะห์ภาพนี้ได้"
    except Exception as e:
        print(f"[image.analyze] {e}")
        return f"❌ วิเคราะห์รูปไม่สำเร็จ: {e}"


def _generate_image_to_file(prompt: str, out_path: str) -> bool:
    """
    สร้างรูปด้วย Images API แล้วเขียนไฟล์ออกไปที่ out_path (png)
    """
    try:
        resp = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        b64 = resp.data[0].b64_json
        if not b64:
            return False

        img_bytes = base64.b64decode(b64)
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        return True
    except Exception as e:
        print(f"[image.generate] {e}")
        return False


# ---------- Main Handler ----------
def handle_image(chat_id: int, msg: dict) -> None:
    """
    ใช้กับอัปเดตรูปภาพ/ข้อความจาก Telegram
    - ถ้ามีรูป: วิเคราะห์รูป
    - ถ้าข้อความขึ้นต้น /imagine: สร้างภาพตาม prompt
    """
    try:
        # 1) เช็กว่ามีข้อความสั่ง /imagine ไหม
        text = (msg.get("text") or msg.get("caption") or "").strip()
        if text.startswith("/imagine"):
            prompt = text[len("/imagine"):].strip() or "a cute orange shiba inu mascot sitting, vector style, transparent background"
            tmp_out = f"/tmp/imagine_{chat_id}.png"
            ok = _generate_image_to_file(prompt, tmp_out)
            if not ok:
                send_message(chat_id, "❌ สร้างภาพไม่สำเร็จครับ ลองใหม่อีกครั้ง")
                return

            if send_photo:
                send_photo(chat_id, tmp_out, caption=f"🖼️ สร้างภาพจากคำสั่ง: {prompt}")
            else:
                send_message(chat_id, "✅ สร้างภาพสำเร็จ (ระบบไม่มีฟังก์ชันส่งรูป ให้โหลดจากไฟล์บนเซิร์ฟเวอร์แทน)")
            if os.path.exists(tmp_out):
                os.remove(tmp_out)
            return

        # 2) ถ้าผู้ใช้ส่งรูปภาพมาให้วิเคราะห์
        photo = msg.get("photo")
        if photo and isinstance(photo, list) and len(photo) > 0:
            # เลือกไซซ์ใหญ่สุด (รายการสุดท้าย)
            largest = photo[-1]
            file_id = largest.get("file_id")
            if not file_id:
                send_message(chat_id, "❌ ไม่พบ file_id ของรูปภาพ")
                return

            # ดาวน์โหลดเป็นไฟล์ชั่วคราว
            local_path = download_telegram_file(file_id, f"photo_{chat_id}.jpg")
            if not local_path:
                send_message(chat_id, "❌ ไม่สามารถโหลดรูปจาก Telegram ได้")
                return

            try:
                hint = text if text else None  # ถ้ามีแคปชัน ใช้เป็น hint
                result = _analyze_image_with_gpt(local_path, user_hint=hint)
                send_message(chat_id, f"🔎 ผลวิเคราะห์ภาพ:\n{result}")
            finally:
                if os.path.exists(local_path):
                    os.remove(local_path)
            return

        # 3) ถ้าไม่ได้ส่งรูป และไม่ได้สั่ง /imagine
        send_message(chat_id, "โปรดส่งรูปมาให้วิเคราะห์ หรือพิมพ์คำสั่ง\n`/imagine คำอธิบายรูป` เพื่อให้ผมสร้างภาพครับ")

    except Exception as e:
        print(f"[handle_image] {e}")
        send_message(chat_id, f"❌ เกิดข้อผิดพลาดระหว่างประมวลผลรูปภาพ: {e}")
