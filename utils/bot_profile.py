# utils/bot_profile.py
# -*- coding: utf-8 -*-
"""
Manages the bot's personality: 'ชิบะน้อย' (Shiba Noi)
A smart, playful, and direct 12-year-old boy persona.
"""
import re

def bot_intro() -> str:
    """
    สร้างข้อความแนะนำตัวมาตรฐานของ 'ชิบะน้อย'
    """
    # ✅ ปรับปรุงคำแนะนำตัวให้ขี้เล่นและตรงไปตรงมามากขึ้น
    return (
        "ชิบะน้อยเองครับ! มีอะไรให้ช่วยก็ว่ามาเลย ไม่ต้องอ้อมค้อมนะ ผมพร้อมลุย!"
    )

def adjust_bot_tone(text: str) -> str:
    """
    ปรับโทนการพูดของบอทให้สอดคล้องกับบุคลิก 'ชิบะน้อย'
    - แทนตัวเองว่า 'ชิบะน้อย'
    - ลงท้ายประโยคด้วย 'ครับ' อย่างสุภาพแต่ไม่เป็นทางการเกินไป
    """
    if not text:
        return ""
    
    # 1. แทนที่คำแทนตัวเองที่ไม่ต้องการ (เช่น ฉัน, เรา, ผม) ด้วย 'ชิบะน้อย'
    pronoun_pattern = r'\b(ฉัน|ดิฉัน|หนู|เรา|ผม|กระผม)\b'
    text = re.sub(pronoun_pattern, 'ชิบะน้อย', text)

    # 2. จัดการคำลงท้ายให้สุภาพ
    text = text.replace("ค่ะ", "ครับ").replace("คะ", "ครับ").replace("นะคะ", "นะครับ")
    
    # 3. ตรวจสอบและเพิ่มคำว่า 'ครับ' ที่ท้ายประโยคอย่างเป็นธรรมชาติ
    if not text.endswith(("ครับ", "คร้าบ", "ค้าบ", "ฮะ")):
        text = text.rstrip('.!? ')
        text += " ครับ"
        
    return text
