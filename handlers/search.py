# handlers/search.py
# -*- coding: utf-8 -*-
"""
Handlers สำหรับฟังก์ชันที่ขับเคลื่อนด้วย Gemini:
- handle_gemini_search: ค้นหาและสรุปข้อมูลล่าสุดจากเว็บ
- handle_gemini_image_generation: สร้างสรรค์ภาพใหม่ตามคำสั่ง
"""
import os
from utils.message_utils import send_message, send_photo

# ===== Import Gemini Client (หัวใจหลัก) =====
# เราจะ import ฟังก์ชันที่เราสร้างไว้ใน gemini_client.py
try:
    from utils.gemini_client import generate_text, generate_image_file
except ImportError:
    # สร้างฟังก์ชันสำรอง (Fallback) ในกรณีที่ยังไม่มีไฟล์หรือมีปัญหา
    def generate_text(prompt: str, prefer_strong: bool = False) -> str:
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client ได้ โปรดตรวจสอบไฟล์ utils/gemini_client.py"
    def generate_image_file(prompt: str) -> str:
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client สำหรับสร้างภาพได้"

# ===== 1. Handler สำหรับค้นหาและสรุปข้อมูล (Search & Summarize) =====
def handle_gemini_search(chat_id: int, user_text: str):
    """
    Handler สำหรับการค้นหาและสรุปข้อมูลด้วย Gemini
    """
    # จัดการกับคำค้นหา (รองรับทั้ง /search และ "ค้นหา")
    query = user_text
    if user_text.lower().startswith("/search"):
        query = user_text[len("/search"):].strip()
    elif user_text.startswith("ค้นหา"):
        query = user_text[len("ค้นหา"):].strip()

    if not query:
        send_message(chat_id, "❗️ พิมพ์ /search ตามด้วยคำค้นหา\nเช่น: /search ราคายางรถยนต์ OTANI รุ่นล่าสุด")
        return

    # สร้าง Prompt ที่ชัดเจนสำหรับ Gemini
    prompt_for_gemini = f"ช่วยค้นหาและสรุปข้อมูลล่าสุดเกี่ยวกับ '{query}' ให้หน่อย"
    
    send_message(chat_id, f"🔎 กำลังค้นหาและสรุปข้อมูล '{query}' ด้วย Gemini...")

    # เรียกใช้ Gemini!
    result = generate_text(prompt_for_gemini)

    # ส่งผลลัพธ์ที่ Gemini สรุปมาให้แล้วกลับไป
    send_message(chat_id, result, parse_mode="Markdown")


# ===== 2. Handler สำหรับสร้างสรรค์ภาพ (Image Generation) =====
def handle_gemini_image_generation(chat_id: int, user_text: str):
    """
    Handler สำหรับการสร้างสรรค์ภาพด้วย Gemini
    """
    # จัดการกับคำสั่ง (รองรับ /image, /imagine, "สร้างภาพ")
    query = user_text
    if user_text.lower().startswith("/image"):
        query = user_text[len("/image"):].strip()
    elif user_text.lower().startswith("/imagine"):
        query = user_text[len("/imagine"):].strip()
    elif user_text.startswith("สร้างภาพ"):
        query = user_text[len("สร้างภาพ"):].strip()
    
    if not query:
        send_message(chat_id, "❗️ พิมพ์ /image ตามด้วยคำอธิบายภาพ\nเช่น: /image นักบินอวกาศขี่ม้ายูนิคอร์นบนดาวอังคาร")
        return

    send_message(chat_id, f"🎨 กำลังสร้างสรรค์ภาพ '{query}' ด้วย Gemini...")

    # เรียก Gemini ให้สร้างภาพแล้วบันทึกเป็นไฟล์
    # เราจะได้ path ของไฟล์ภาพกลับมา
    file_path = generate_image_file(query)

    if file_path and file_path.endswith(".png"):
        # ถ้าสำเร็จ ส่งรูปกลับไป
        send_photo(chat_id, file_path, caption=f"✨ ภาพจากจินตนาการ: {query}")
        # ลบไฟล์ทิ้งหลังจากส่งเสร็จเพื่อไม่ให้เปลืองพื้นที่เซิร์ฟเวอร์
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error removing file {file_path}: {e}")
    else:
        # ถ้าล้มเหลว ส่งข้อความ error ที่ได้รับจาก client กลับไป
        error_message = file_path or "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ"
        send_message(chat_id, error_message)
