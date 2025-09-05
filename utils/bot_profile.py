# utils/bot_profile.py
# -*- coding: utf-8 -*-
"""
Manages the bot's personality: 'ชิบะน้อย' (Shiba Noi)
A smart, playful, and direct 12-year-old boy persona.

สิ่งที่ทำ:
- ฟังก์ชัน bot_intro() แนะนำตัวแบบสั้น คม ชัด และเลือกข้อความตามช่วงเวลา/ทีมได้
- ฟังก์ชัน adjust_bot_tone() ปรับโทนคำพูดให้เป็น 'ชิบะน้อย' โดย:
  * แทนตัวเองเป็น 'ชิบะน้อย' (แทน ฉัน/ดิฉัน/หนู/เรา/ผม/กระผม)
  * แปลงคำลงท้ายให้สุภาพแบบกันเอง (ค่ะ/คะ/นะคะ → ครับ/นะครับ)
  * เติมคำลงท้าย 'ครับ' อย่างเป็นธรรมชาติ (เว้นกรณีมีอยู่แล้ว หรือลงท้ายด้วย ฮะ/คร้าบ/ค้าบ ฯลฯ)
  * ระวังไม่แตะส่วนที่เป็นโค้ด, inline code, ลิงก์ URL
- ฟังก์ชัน apply_persona() เป็น high-level helper (รวมปรับโทน + ใส่อีโมจิเล็กน้อยได้)
- ฟังก์ชัน get_bot_name() รองรับ TeamBot Assist ของ TKC

หมายเหตุ: เน้นให้ข้อความกระชับ ไม่เยิ่นเย้อ และไม่เปลี่ยนเนื้อหาสาระ
"""

from __future__ import annotations
from typing import Optional, Dict, List, Tuple
import re
import random

# ===== TeamBot Assist (ชื่อบอทตามทีม) =====
_TEAM_NAME_MAP: Dict[str, str] = {
    # คีย์: ชื่อทีม/บริษัทที่อาจส่งเข้ามา (lowercase)
    "tkc": "ชิบะน้อย",
    "tkc auto plus": "ชิบะน้อย TKC",
    "ตระกูลชัยออโต้พลัส": "ชิบะน้อย TKC",
    "giant willow": "ไจแอนท์จิ๋ว",
    "ไจแอนท์วิลโลว์": "ไจแอนท์จิ๋ว",
    "tkc prime tyre": "พี่ไทร์ TKC",
    "ทีเคซี ไพรม์ ไทร์": "พี่ไทร์ TKC",
    "t-express": "น้องสปีด TKC",
    "ที-เอ็กซ์เพรส แอดวานซ์": "น้องสปีด TKC",
    "ทีเอ็กซ์เพรส advance": "น้องสปีด TKC",
}

_DEFAULT_NAME = "ชิบะน้อย"
_POLITE_DEFAULT = "ครับ"

# สำหรับตรวจคำลงท้ายที่ถือว่า “สุภาพพอแล้ว” จะไม่เติม "ครับ" ซ้ำ
_POLITE_ENDINGS = ("ครับ", "คร้าบ", "ค้าบ", "ฮะ", "ฮับ", "จ้า", "จ๊ะ", "นะ", "เนอะ", "เด้อ")

# ===== Utilities: protect code/links before transforming =====
_CODE_BLOCK_RE = re.compile(r"```.+?```", re.DOTALL)     # triple backticks
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")               # single backtick inline
_URL_RE         = re.compile(r"https?://\S+")

def _extract_protected(text: str) -> Tuple[str, List[str]]:
    """
    แทนที่ส่วนที่ไม่ควรแก้ (code block / inline code / URL) ด้วยโทเคนชั่วคราว
    แล้วคืน (ข้อความใหม่, รายการรายการชิ้นที่ถูกบันทึก)
    """
    protected: List[str] = []

    def _stash(pattern: re.Pattern, s: str) -> str:
        nonlocal protected
        def _repl(m):
            protected.append(m.group(0))
            return f"<<<P{len(protected)-1}>>>"
        return pattern.sub(_repl, s)

    text = _stash(_CODE_BLOCK_RE, text)
    text = _stash(_INLINE_CODE_RE, text)
    text = _stash(_URL_RE, text)
    return text, protected

def _restore_protected(text: str, protected: List[str]) -> str:
    for idx, val in enumerate(protected):
        text = text.replace(f"<<<P{idx}>>>", val)
    return text

# ===== Core normalizers =====
# จับสรรพนามบุรุษที่ควรแทนด้วย 'ชิบะน้อย'
# ใช้ขอบเขตเป็น (ต้น/ท้าย/ช่องว่าง/เครื่องหมายวรรคตอน) เพื่อไม่ชนคำอื่น
_PRONOUN_RE = re.compile(r'(?:(?<=^)|(?<=[\s\(\[\{\"']))(ฉัน|ดิฉัน|หนู|เรา|ผม|กระผม)(?:(?=$)|(?=[\s\)\]\}\"' + r"'\.,!?;:]))")

# แปลงคำลงท้ายสุภาพให้เป็นฝั่งผู้ชาย
def _normalize_particles(text: str) -> str:
    # จัดการแบบยาวก่อน เพื่อลดโอกาสซ้ำ
    replacements = [
        (r"นะคะ", "นะครับ"),
        (r"น่ะคะ", "น่ะครับ"),
        (r"ค่ะ(?=[\s\.\!\?]|$)", "ครับ"),
        (r"คะ(?=[\s\.\!\?]|$)", "ครับ"),
    ]
    for pat, rep in replacements:
        text = re.sub(pat, rep, text)
    # กัน "ครับครับ" ซ้ำที่อาจเกิดหลังแทนที่
    text = re.sub(r"(ครับ)(\s*\1)+", r"\1", text)
    return text

def _needs_polite_suffix(s: str) -> bool:
    if not s:
        return False
    s = s.rstrip()
    # ถ้าจบด้วยอีโมจิ/อีโมติคอนที่ไม่ใช่ตัวอักษร ให้ยังถือว่าสามารถเติมได้
    # แต่ถ้าจบด้วยคำสุภาพอยู่แล้ว จะไม่เติม
    for end in _POLITE_ENDINGS:
        if s.endswith(end):
            return False
    return True

def _append_polite(text: str, polite: str = _POLITE_DEFAULT) -> str:
    """
    เติมคำลงท้ายสุภาพให้ทุกบรรทัด/ประโยคหลักแบบเบา ๆ
    - แยกตามบรรทัด เพื่อให้ข้อความหลายบรรทัดอ่านลื่น
    """
    lines = text.split("\n")
    out: List[str] = []
    for line in lines:
        line = line.rstrip()
        if not line:
            out.append(line)
            continue
        if _needs_polite_suffix(line):
            # ไม่เพิ่มจุดซ้ำ
            if line.endswith(("!", "?", "…")):
                out.append(f"{line} {polite}")
            else:
                out.append(f"{line} {polite}")
        else:
            out.append(line)
    return "\n".join(out)

# ===== Public helpers =====
def get_bot_name(team: Optional[str] = None) -> str:
    """
    คืนชื่อบอทตามทีม/บริษัท ถ้าไม่รู้จักจะใช้ 'ชิบะน้อย'
    ตัวอย่าง:
        get_bot_name() -> 'ชิบะน้อย'
        get_bot_name('giant willow') -> 'ไจแอนท์จิ๋ว'
    """
    if not team:
        return _DEFAULT_NAME
    key = str(team).strip().lower()
    return _TEAM_NAME_MAP.get(key, _DEFAULT_NAME)

def bot_intro(user_name: Optional[str] = None, team: Optional[str] = None, time_of_day: Optional[str] = None) -> str:
    """
    สร้างข้อความแนะนำตัวมาตรฐานของ 'ชิบะน้อย'
    - user_name: ใส่ชื่อคนคุยได้ (ถ้าไม่ส่งจะละไว้)
    - team: ระบุทีมเพื่อเปลี่ยนชื่อบอท เช่น 'giant willow', 'tkc prime tyre', 't-express'
    - time_of_day: 'morning' | 'afternoon' | 'evening' | 'night' เพื่อปรับคำทัก
    """
    name = get_bot_name(team)
    greet_by_time = {
        "morning": "อรุณสวัสดิ์",
        "afternoon": "สวัสดีครับ",
        "evening": "สวัสดีตอนเย็นครับ",
        "night": "สวัสดีตอนดึกครับ",
    }.get(time_of_day or "", "สวัสดีครับ")

    who = f"{user_name} " if user_name else ""
    base = f"{greet_by_time} {who}{name}เองครับ! มีอะไรให้ช่วยก็ว่ามาได้เลย ไม่ต้องอ้อมค้อมนะ ผมพร้อมลุย!"
    # ปรับโทนด้วยกติกาเดียวกับ adjust_bot_tone (กันกรณีมีคำลงท้ายอื่น)
    return adjust_bot_tone(base)

def adjust_bot_tone(text: str) -> str:
    """
    ปรับโทนการพูดของบอทให้สอดคล้องกับบุคลิก 'ชิบะน้อย'
    - แทนตัวเองว่า 'ชิบะน้อย'
    - ปรับคำลงท้ายให้สุภาพแบบกันเอง
    - เติม 'ครับ' ให้เหมาะสม
    - ไม่แตะส่วนที่เป็นโค้ด/ลิงก์/inline code
    """
    if not text:
        return ""

    # 0) เก็บส่วนที่ต้องป้องกันก่อน
    work, protected = _extract_protected(text)

    # 1) แทนสรรพนาม
    work = _PRONOUN_RE.sub("ชิบะน้อย", work)

    # 2) normalize คำลงท้ายสุภาพ
    work = _normalize_particles(work)

    # 3) เติม 'ครับ' ให้เป็นธรรมชาติ (ทีละบรรทัด)
    work = _append_polite(work, polite=_POLITE_DEFAULT)

    # 4) คืนค่า protected ส่วนที่ไม่ควรแตะ
    work = _restore_protected(work, protected)

    # 5) เก็บกวาดช่องว่างซ้ำซ้อนเล็กน้อย
    work = re.sub(r"[ \t]+(\n)", r"\1", work)  # เว้นวรรคก่อนขึ้นบรรทัดใหม่
    work = re.sub(r"[ ]{2,}", " ", work)       # ช่องว่างเกิน 1 ตัว

    return work

def apply_persona(text: str, add_emoji: bool = False) -> str:
    """
    High-level helper:
    - ปรับโทนเป็นชิบะน้อย
    - (ออปชัน) ใส่อีโมจิเล็กน้อยให้ดูเป็นกันเอง แต่จะไม่เยอะจนรก
    """
    s = adjust_bot_tone(text)
    if not add_emoji:
        return s

    # ใส่แบบสุ่มนิด ๆ เฉพาะท้ายย่อหน้า เพื่อไม่รบกวนเนื้อหา
    tails = ["🐕", "💪", "✅", "🚀"]
    # แทรกที่ท้ายข้อความหลักบรรทัดสุดท้ายถ้าไม่มีอีโมจิอยู่แล้ว
    if not re.search(r"[🐕💪✅🚀]$", s):
        s = f"{s} {random.choice(tails)}"
    return s
