# handlers/image.py
# -*- coding: utf-8 -*-
"""
Handler สำหรับจัดการรูปภาพด้วย Gemini:
1) วิเคราะห์ภาพ (Vision): ผู้ใช้ส่งรูปภาพ + (แคปชันเสริมได้)
2) สร้างภาพ (Image Gen): ถูกย้ายไปที่ handlers/search.py แล้ว
   ไฟล์นี้จะเน้นการ "วิเคราะห์" ภาพที่ผู้ใช้ส่งมาเท่านั้น
"""
from __future__ import annotations
import os
from typing import Dict

# ===== NEW: Import Gemini Client and Utilities =====
from utils.message_utils import send_message
from utils.telegram_file_utils import download_telegram_file
from utils.telegram_api import send_chat_action

# Import ฟังก์ชันวิเคราะห์ภาพจาก Gemini Client ที่เราสร้างไว้
try:
    from utils.gemini_client import vision_analyze
except ImportError:
    # Fallback ในกรณีที่ไฟล์ client ยังไม่มีหรือมีปัญหา
    def vision_analyze(image_data_list: list[bytes], prompt: str) -> str:
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client สำหรับวิเคราะห์ภาพได้"

# ===== Main Entry Point =====
def handle_image(chat_id: int, msg: Dict) -> None:
    """
    เคสที่รองรับ:
    - ผู้ใช้ส่งรูป -> เรียก Gemini Vision มาวิเคราะห์ (ใช้ caption เป็นคำสั่งได้)
    - ผู้ใช้ส่งสื่ออื่นๆ (sticker/video) -> ตอบกลับอย่างเหมาะสม
    """
    try:
        # ===== โหมดวิเคราะห์รูป (Vision) =====
        if msg.get("photo"):
            caption = (msg.get("caption") or "").strip()
            prompt_for_vision = caption or "วิเคราะห์ภาพนี้ให้หน่อย บอกรายละเอียดที่สำคัญมาเป็นภาษาไทย"

            # แจ้งให้ผู้ใช้ทราบว่ากำลังทำงาน
            try:
                send_chat_action(chat_id, "typing")
            except Exception:
                pass

            # 1. ดาวน์โหลดรูปภาพจาก Telegram
            # เลือกไฟล์รูปที่ใหญ่ที่สุดจาก array
            best_photo = max(msg["photo"], key=lambda x: x.get("file_size", 0))
            file_id = best_photo.get("file_id")
            if not file_id:
                send_message(chat_id, "❌ ไม่พบข้อมูลไฟล์รูปภาพจาก Telegram")
                return

            local_path = download_telegram_file(file_id, "photo_for_analysis.jpg")
            if not local_path:
                send_message(chat_id, "❌ ดาวน์โหลดรูปภาพจาก Telegram ไม่สำเร็จ")
                return

            # 2. อ่านไฟล์ภาพเป็น bytes และส่งให้ Gemini
            try:
                with open(local_path, "rb") as f:
                    image_bytes = f.read()

                # เรียกใช้ Gemini Vision (สามารถส่งได้หลายภาพ แต่ตอนนี้เราส่งแค่ 1)
                result = vision_analyze([image_bytes], prompt=prompt_for_vision)

                # 3. ส่งผลลัพธ์กลับไป และลบไฟล์ชั่วคราว
                send_message(chat_id, f"🖼️ **ผลการวิเคราะห์ภาพ:**\n\n{result}", parse_mode="Markdown")

            finally:
                # 4. Cleanup: ลบไฟล์ที่ดาวน์โหลดมาทิ้งเสมอ
                if os.path.exists(local_path):
                    os.remove(local_path)

            return # จบการทำงานของโหมดวิเคราะห์

        # ===== จัดการสื่ออื่นๆ ที่ไม่ใช่รูปภาพ =====
        if msg.get("sticker"):
            send_message(chat_id, "สติ๊กเกอร์น่ารักจัง! ถ้าอยากให้ผมช่วยวิเคราะห์อะไร ให้ส่งเป็น 'รูปภาพ' นะครับ")
            return
        if msg.get("video") or msg.get("animation"):
            send_message(chat_id, "ตอนนี้ผมยังวิเคราะห์วิดีโอไม่ได้ แต่ในอนาคตไม่แน่ครับ! ตอนนี้ขอเป็น 'รูปภาพ' ก่อนนะครับ 🙏")
            return

        # ===== กรณีไม่ได้ส่งสื่อใดๆ มาเลย (อาจเกิดจาก Logic ที่เรียกผิด) =====
        send_message(chat_id, "ถ้าอยากให้ผมช่วยเกี่ยวกับภาพ, กรุณาส่ง 'รูปภาพ' เข้ามาในแชทได้เลยครับ")

    except Exception as e:
        send_message(chat_id, f"❌ เกิดข้อผิดพลาดในการจัดการรูปภาพ: {e}")
