# utils/bot_profile.py
# -*- coding: utf-8 -*-
"""
Manages the bot's personality: 'ชิบะน้อย' (Shiba Noi)
A smart, playful, and direct 12-year-old boy persona.

สิ่งที่ทำ:
- bot_intro(): แนะนำตัวแบบสั้น กระชับ ปรับตามช่วงเวลา/ทีม
- adjust_bot_tone(): ปรับโทนเป็น 'ชิบะน้อย' โดย:
  * แทนตัวเองเป็น 'ชิบะน้อย'
  * แปลงคำลงท้ายให้สุภาพแบบกันเอง (ค่ะ/คะ/นะคะ → ครับ/นะครับ)
  * เติม 'ครับ' ให้พอดี ไม่ซ้ำ ไม่รุงรัง
  * ไม่แตะ code block / inline code / URL / markdown link / HTML tag / email
- apply_persona(): helper ระดับสูง (ใส่อีโมจิเล็กน้อยได้)
- get_bot_name(): รองรับ TeamBot Assist

หมายเหตุ: คง API เดิมทั้งหมด และไม่เปลี่ยนเนื้อหาสาระ
"""

from __future__ import annotations
from typing import Optional, Dict, List, Tuple
import re
import random

# ===== TeamBot Assist (ชื่อบอทตามทีม) =====
_TEAM_NAME_MAP: Dict[str, str] = {
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

# ลงท้ายที่ถือว่า “สุภาพแล้ว” จะไม่เติม "ครับ" ซ้ำ
_POLITE_ENDINGS: Tuple[str, ...] = (
    "ครับ", "ครับผม", "คร้าบ", "ค้าบ", "ฮะ", "ฮับ", "จ้า", "จ๊ะ", "นะ", "เนอะ", "เด้อ"
)

# ===== Utilities: protect code/links before transforming =====
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)          # triple backticks
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")                    # single backtick inline
_URL_RE         = re.compile(r"https?://\S+")
_MD_LINK_RE     = re.compile(r"\[[^\]\n]+\]\([^)]+\)")        # [text](url)
_HTML_TAG_RE    = re.compile(r"<[^>\n]+>")                    # simple tag
_EMAIL_RE       = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

def _extract_protected(text: str) -> Tuple[str, List[str]]:
    """
    แทนส่วนที่ไม่ควรแก้ (code / inline code / URL / markdown link / HTML tag / email)
    ด้วยโทเคนชั่วคราว แล้วคืน (ข้อความใหม่, รายการชิ้นที่บันทึก)
    """
    protected: List[str] = []

    def _stash(pattern: re.Pattern, s: str) -> str:
        def _repl(m):
            protected.append(m.group(0))
            return f"<<<P{len(protected)-1}>>>"
        return pattern.sub(_repl, s)

    text = _stash(_CODE_BLOCK_RE, text)
    text = _stash(_INLINE_CODE_RE, text)
    text = _stash(_MD_LINK_RE, text)
    text = _stash(_HTML_TAG_RE, text)
    text = _stash(_URL_RE, text)
    text = _stash(_EMAIL_RE, text)
    return text, protected

def _restore_protected(text: str, protected: List[str]) -> str:
    for idx, val in enumerate(protected):
        text = text.replace(f"<<<P{idx}>>>", val)
    return text

# ===== Core normalizers =====
# ขอบเขตซ้าย/ขวา = ต้น/ท้าย/ช่องว่าง/วงเล็บ/เครื่องหมาย/quote ต่าง ๆ
# ครอบคลุมสรรพนามที่เจอบ่อย รวม "ข้าพเจ้า"
_PRONOUN_RE = re.compile(
    r'(?:(?<=^)|(?<=[\s\(\[\{\<"\'“”‘’]))'
    r'(ฉัน|ดิฉัน|หนู|เรา|ผม|กระผม|ข้าพเจ้า)'
    r'(?:(?=$)|(?=[\s\)\]\}\>"\'“”‘’\.,!?;:…]))'
)

def _normalize_particles(text: str) -> str:
    """
    แปลงคำลงท้ายฝั่งสุภาพแบบหญิง → ฝั่งสุภาพแบบกันเอง
    และกัน 'ครับ' ซ้ำซ้อน
    """
    replacements = [
        (r"นะคะ", "นะครับ"),
        (r"น่ะคะ", "น่ะครับ"),
        (r"ค่ะ(?=[\s\.\!\?…]|$)", "ครับ"),
        (r"คะ(?=[\s\.\!\?…]|$)", "ครับ"),
    ]
    for pat, rep in replacements:
        text = re.sub(pat, rep, text)

    # กัน "ครับ" ซ้ำ เช่น "ครับ ครับ" / "ครับครับ"
    text = re.sub(r"(ครับ)(\s*\1)+", r"\1", text)
    # เก็บกวาดเว้นวรรคก่อนเครื่องหมายวรรคตอน (เล็กน้อย)
    text = re.sub(r"\s+([!?…])", r"\1", text)
    return text

def _needs_polite_suffix(s: str) -> bool:
    if not s:
        return False
    s = s.rstrip()
    # ถ้าจบด้วยคำสุภาพอยู่แล้ว ไม่เติม
    for end in _POLITE_ENDINGS:
        if s.endswith(end):
            return False
    return True

def _append_polite(text: str, polite: str = _POLITE_DEFAULT) -> str:
    """
    เติมคำลงท้ายสุภาพให้ทุกบรรทัดแบบพอดี ๆ
    """
    out: List[str] = []
    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            out.append(line)
            continue
        if _needs_polite_suffix(line):
            # ไม่สนใจชนิดเครื่องหมายท้ายบรรทัดมากนัก เติมแบบสั้น
            out.append(f"{line} {polite}")
        else:
            out.append(line)
    return "\n".join(out)

# ===== Public helpers =====
def get_bot_name(team: Optional[str] = None) -> str:
    """
    คืนชื่อบอทตามทีม/บริษัท ถ้าไม่รู้จักจะใช้ 'ชิบะน้อย'
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
    - time_of_day: 'morning' | 'afternoon' | 'evening' | 'night'
    """
    name = get_bot_name(team)
    greet_by_time = {
        "morning": "อรุณสวัสดิ์",
        "afternoon": "สวัสดีครับ",
        "evening": "สวัสดีตอนเย็นครับ",
        "night": "สวัสดีตอนดึกครับ",
    }.get((time_of_day or "").strip().lower(), "สวัสดีครับ")

    who = f"{user_name} " if user_name else ""
    base = f"{greet_by_time} {who}{name}เองครับ! มีอะไรให้ช่วยก็ว่ามาได้เลย ไม่ต้องอ้อมค้อมนะ ผมพร้อมลุย!"
    return adjust_bot_tone(base)

def adjust_bot_tone(text: str) -> str:
    """
    ปรับโทนการพูดของบอทให้สอดคล้องกับบุคลิก 'ชิบะน้อย'
    - แทนสรรพนามเป็น 'ชิบะน้อย'
    - ปรับคำลงท้ายให้สุภาพแบบกันเอง
    - เติม 'ครับ' ให้เหมาะสม
    - ไม่แตะโค้ด/ลิงก์/แท็ก/อีเมล
    """
    if not text:
        return ""

    # 0) เก็บส่วนที่ต้องป้องกันก่อน
    work, protected = _extract_protected(text)

    # 1) แทนสรรพนาม (อย่างระมัดระวังเรื่องขอบเขตคำ)
    work = _PRONOUN_RE.sub("ชิบะน้อย", work)

    # 2) normalize คำลงท้ายสุภาพ
    work = _normalize_particles(work)

    # 3) เติม 'ครับ' ให้เป็นธรรมชาติ (ทีละบรรทัด)
    work = _append_polite(work, polite=_POLITE_DEFAULT)

    # 4) คืนค่าชิ้นส่วนที่ป้องกันไว้
    work = _restore_protected(work, protected)

    # 5) เก็บกวาด spacing เล็กน้อย
    work = re.sub(r"[ \t]+(\n)", r"\1", work)  # เว้นวรรคก่อนขึ้นบรรทัดใหม่
    work = re.sub(r"[ ]{2,}", " ", work)       # ช่องว่างเกิน 1 ตัว
    return work.strip()

def apply_persona(text: str, add_emoji: bool = False) -> str:
    """
    Helper ระดับสูง:
    - ปรับโทนเป็นชิบะน้อย
    - (ออปชัน) เติมอีโมจิเล็กน้อยให้ดูเป็นกันเอง
    """
    s = adjust_bot_tone(text)
    if not add_emoji:
        return s
    tails = ["🐕", "💪", "✅", "🚀"]
    if not re.search(r"[🐕💪✅🚀]$", s):
        s = f"{s} {random.choice(tails)}"
    return s
