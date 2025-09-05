# handlers/image.py
# -*- coding: utf-8 -*-
"""
Handler สำหรับ 'วิเคราะห์ภาพ' เท่านั้น (ไม่รวมการสร้างภาพ)
รองรับ:
1) ผู้ใช้ส่งรูปแบบ Telegram photo (msg['photo'])
2) ผู้ใช้ส่งไฟล์เป็น document ที่เป็นภาพ (mime_type เริ่มด้วย image/)

มาตรฐานความเสถียร:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo)
- แสดง typing action ระหว่างประมวลผล
- parse_mode=HTML พร้อม escape ข้อความทุกจุด
- กัน path traversal และจำกัดขนาดไฟล์
"""

from __future__ import annotations
import os
import uuid
from typing import Dict, Any, List

from utils.message_utils import send_message, send_typing_action
from utils.telegram_file_utils import download_telegram_file

# Gemini Vision client (fallback หากไม่มี)
try:
    from utils.gemini_client import vision_analyze  # expected: (images: List[bytes], prompt: str) -> str
except Exception:
    def vision_analyze(image_data_list: List[bytes], prompt: str) -> str:  # type: ignore
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client สำหรับวิเคราะห์ภาพได้"

# ===== Config via ENV =====
_IMAGE_MAX_BYTES = int(os.getenv("IMAGE_MAX_BYTES", str(20 * 1024 * 1024)))  # ดีฟอลต์ 20MB

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _best_photo_file(msg_photo_list: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """
    เลือกตัวที่ใหญ่ที่สุดจาก msg['photo'] (แต่ละตัวคือ size ต่างกันของรูปเดียวกัน)
    """
    if not msg_photo_list:
        return None
    def _score(p):
        fs = p.get("file_size") or 0
        # กันกรณีไม่มี file_size: ใช้พื้นที่โดยประมาณ
        wh = (p.get("width") or 0) * (p.get("height") or 0)
        return (fs, wh)
    return max(msg_photo_list, key=_score)

def _is_image_document(doc: Dict[str, Any]) -> bool:
    mime = (doc.get("mime_type") or "").lower()
    return mime.startswith("image/")

def _safe_name(base: str, suffix: str = ".jpg") -> str:
    """กัน path traversal + ใส่ UUID กันชนกันชื่อซ้ำ"""
    base = os.path.basename(base or "image")
    # ตัดนามสกุลเดิมทิ้งแล้วใช้ suffix ที่เรากำหนด เพื่อ normalize ชนิดไฟล์ชั่วคราว
    name, _ext = os.path.splitext(base)
    return f"{name[:40]}_{uuid.uuid4().hex[:8]}{suffix}"

# ===== Main Entry Point =====
def handle_image(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """
    วิเคราะห์รูปภาพด้วย Gemini Vision
    - ใช้ caption เป็น prompt ได้; ถ้าไม่ระบุจะใช้ prompt ดีฟอลต์
    - รองรับรูปจาก msg['photo'] และ document ที่เป็นภาพ (image/*)
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        # ==== รองรับรูปแบบ 'photo' ของ Telegram ====
        if msg.get("photo"):
            best = _best_photo_file(msg["photo"])
            if not best or not best.get("file_id"):
                send_message(chat_id, "❌ ไม่พบข้อมูลไฟล์รูปภาพจาก Telegram", parse_mode="HTML")
                return

            caption = (msg.get("caption") or "").strip()
            prompt = caption or "วิเคราะห์ภาพนี้ให้หน่อย บอกรายละเอียดสำคัญเป็นภาษาไทย"

            # แจ้งสถานะ
            send_typing_action(chat_id, "typing")

            # ดาวน์โหลด
            safe_filename = _safe_name("photo.jpg", ".jpg")
            local_path = download_telegram_file(best["file_id"], safe_filename)
            if not local_path or not os.path.exists(local_path):
                send_message(chat_id, "❌ ดาวน์โหลดรูปภาพจาก Telegram ไม่สำเร็จครับ", parse_mode="HTML")
                return

            try:
                # จำกัดขนาดไฟล์
                try:
                    if os.path.getsize(local_path) > _IMAGE_MAX_BYTES:
                        send_message(
                            chat_id,
                            f"❌ ไฟล์รูปใหญ่เกินไปครับ (ขีดจำกัด ~{_IMAGE_MAX_BYTES // (1024*1024)}MB) "
                            f"โปรดส่งรูปที่เล็กกว่านี้",
                            parse_mode="HTML",
                        )
                        return
                except Exception:
                    pass

                with open(local_path, "rb") as f:
                    img_bytes = f.read()

                send_typing_action(chat_id, "typing")
                result = vision_analyze([img_bytes], prompt=prompt) or "⚠️ ไม่พบผลลัพธ์จากการวิเคราะห์"

                # ส่งผลลัพธ์ (escape เพื่อกันฟอร์แมตพัง)
                send_message(
                    chat_id,
                    f"🖼️ <b>ผลการวิเคราะห์ภาพ</b>\n\n{_html_escape(result)}",
                    parse_mode="HTML",
                )
            finally:
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except Exception:
                    pass
            return

        # ==== รองรับกรณีส่งรูปเป็น document (image/*) ====
        if msg.get("document") and _is_image_document(msg["document"]):
            doc = msg["document"]
            file_id = doc.get("file_id")
            if not file_id:
                send_message(chat_id, "❌ ไม่พบข้อมูลไฟล์รูปภาพจาก Telegram", parse_mode="HTML")
                return

            caption = (msg.get("caption") or "").strip()
            prompt = caption or "วิเคราะห์ภาพนี้ให้หน่อย บอกรายละเอียดสำคัญเป็นภาษาไทย"

            send_typing_action(chat_id, "typing")
            orig_name = doc.get("file_name") or "image"
            # สร้างชื่อไฟล์ปลอดภัยและคงสกุลคร่าว ๆ จาก mime type
            suffix = ".png" if (doc.get("mime_type") or "").lower().endswith("png") else ".jpg"
            safe_filename = _safe_name(orig_name, suffix)
            local_path = download_telegram_file(file_id, safe_filename)
            if not local_path or not os.path.exists(local_path):
                send_message(chat_id, "❌ ดาวน์โหลดรูปภาพจาก Telegram ไม่สำเร็จครับ", parse_mode="HTML")
                return

            try:
                try:
                    if os.path.getsize(local_path) > _IMAGE_MAX_BYTES:
                        send_message(
                            chat_id,
                            f"❌ ไฟล์รูปใหญ่เกินไปครับ (ขีดจำกัด ~{_IMAGE_MAX_BYTES // (1024*1024)}MB) "
                            f"โปรดส่งรูปที่เล็กกว่านี้",
                            parse_mode="HTML",
                        )
                        return
                except Exception:
                    pass

                with open(local_path, "rb") as f:
                    img_bytes = f.read()

                send_typing_action(chat_id, "typing")
                result = vision_analyze([img_bytes], prompt=prompt) or "⚠️ ไม่พบผลลัพธ์จากการวิเคราะห์"

                send_message(
                    chat_id,
                    f"🖼️ <b>ผลการวิเคราะห์ภาพ</b>\n\n{_html_escape(result)}",
                    parse_mode="HTML",
                )
            finally:
                try:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                except Exception:
                    pass
            return

        # ==== จัดการสื่ออื่น ๆ ====
        if msg.get("sticker"):
            send_message(chat_id, "สติ๊กเกอร์น่ารักจัง! ถ้าอยากให้ผมวิเคราะห์อะไร ให้ส่งเป็น ‘รูปภาพ’ นะครับ", parse_mode="HTML")
            return
        if msg.get("video") or msg.get("animation"):
            send_message(chat_id, "ตอนนี้ผมยังวิเคราะห์วิดีโอไม่ได้ครับ — ส่งเป็นรูปภาพแทนก่อนนะครับ 🙏", parse_mode="HTML")
            return

        # ไม่พบสื่อ
        send_message(chat_id, "ถ้าอยากให้ผมช่วยวิเคราะห์ภาพ กรุณาส่ง ‘รูปภาพ’ เข้ามาในแชทได้เลยครับ", parse_mode="HTML")

    except Exception as e:
        # ไม่ส่ง traceback ให้ผู้ใช้
        print(f"[handle_image] ERROR: {e}")
        send_message(chat_id, "❌ เกิดข้อผิดพลาดในการจัดการรูปภาพครับ", parse_mode="HTML")
