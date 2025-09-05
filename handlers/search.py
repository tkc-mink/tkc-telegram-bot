# handlers/search.py
# -*- coding: utf-8 -*-
"""
Handlers สำหรับฟังก์ชันที่ขับเคลื่อนด้วย Gemini:
- handle_gemini_search: ค้นหาและสรุปข้อมูลล่าสุดจากเว็บ (สไตล์ text)
- handle_gemini_image_generation: สร้างสรรค์ภาพใหม่ตามคำสั่ง

เวอร์ชันเสถียร:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo + typing action)
- parse_mode=HTML พร้อม escape ข้อความภายนอก
- รองรับ signature แบบใหม่ (user_info, user_text) และ legacy (chat_id, user_text)
- ลบไฟล์ชั่วคราวเสมอหลังส่งภาพ
- จำกัดขนาดไฟล์ภาพตาม ENV: IMAGE_GEN_MAX_BYTES (ดีฟอลต์ 10MB)
"""

from __future__ import annotations
import os
import uuid
from typing import Dict, Any, Tuple

from utils.message_utils import send_message, send_photo, send_typing_action

# ===== Gemini Client =====
try:
    from utils.gemini_client import generate_text, generate_image_file  # type: ignore
except Exception:
    def generate_text(prompt: str, prefer_strong: bool = False) -> str:  # type: ignore
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client ได้ โปรดตรวจสอบไฟล์ <code>utils/gemini_client.py</code>"
    def generate_image_file(prompt: str) -> str:  # type: ignore
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client สำหรับสร้างภาพได้"

# ===== Config via ENV =====
_IMAGE_GEN_MAX_BYTES = int(os.getenv("IMAGE_GEN_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _looks_html(s: str) -> bool:
    if not s:
        return False
    return ("</" in s) or ("<b>" in s) or ("<i>" in s) or ("<code>" in s) or ("<a " in s) or ("<br" in s)

def _strip_command_prefix(user_text: str, *prefixes: str) -> str:
    """ตัด prefix คำสั่งออก เช่น /search, /imagine, 'ค้นหา', 'สร้างภาพ'"""
    t = (user_text or "").strip()
    low = t.lower()
    for p in prefixes:
        if low.startswith(p.lower()):
            return t[len(p):].strip()
    return t

def _normalize_query_for_search(user_text: str) -> str:
    # รองรับ /search, 'ค้นหา'
    q = _strip_command_prefix(user_text, "/search", "ค้นหา")
    return q

def _normalize_query_for_image(user_text: str) -> str:
    # รองรับ /image, /imagine, 'สร้างภาพ'
    q = _strip_command_prefix(user_text, "/image", "/imagine", "สร้างภาพ")
    return q

def _safe_temp_name(ext: str = ".png") -> str:
    return f"img_{uuid.uuid4().hex[:8]}{ext}"

def _send_text_result(chat_id: int | str, query: str, result: str) -> None:
    """ส่งผลลัพธ์ text โดยพิจารณา HTML/escape ให้เหมาะสม"""
    if not result:
        send_message(chat_id, "⚠️ ไม่พบข้อมูลที่สรุปได้ในขณะนี้ครับ", parse_mode="HTML")
        return
    if _looks_html(result):
        send_message(chat_id, result, parse_mode="HTML")
    else:
        send_message(
            chat_id,
            f"🔎 <b>สรุปข้อมูลล่าสุด</b> — <code>{_html_escape(query)}</code>\n\n{_html_escape(result)}",
            parse_mode="HTML",
        )

def _send_image_file(chat_id: int | str, file_path: str, caption: str) -> None:
    """
    ส่งภาพด้วย send_photo ของ message_utils (ซึ่งรองรับทั้ง URL/ไฟล์ท้องถิ่นผ่าน helper ภายใน)
    และลบไฟล์ท้องถิ่นหลังส่ง
    """
    try:
        if not (file_path and os.path.exists(file_path)):
            send_message(chat_id, "❌ ไม่พบไฟล์ภาพที่สร้างขึ้นครับ", parse_mode="HTML")
            return

        # จำกัดขนาดไฟล์
        try:
            sz = os.path.getsize(file_path)
            if sz > _IMAGE_GEN_MAX_BYTES:
                send_message(
                    chat_id,
                    f"❌ ไฟล์ภาพใหญ่เกินไปครับ (จำกัด ~{_IMAGE_GEN_MAX_BYTES // (1024*1024)}MB) "
                    f"โปรดลองปรับคำสั่งให้ภาพเล็กลง",
                    parse_mode="HTML",
                )
                return
        except Exception:
            pass

        # ส่งรูป
        send_photo(chat_id, file_path, caption=_html_escape(caption), parse_mode="HTML")
    finally:
        # ลบไฟล์เสมอ
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

# =====================================================================
# 1) Search & Summarize (Signature ใหม่: รับ user_info)
# =====================================================================
def handle_gemini_search(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    query = _normalize_query_for_search(user_text)

    if not query:
        send_message(
            chat_id,
            "❗️ วิธีใช้: <code>/search &lt;คำค้น&gt;</code>\n"
            "เช่น <code>/search ราคายางรถยนต์ OTANI รุ่นล่าสุด</code>",
            parse_mode="HTML",
        )
        return

    # แจ้งสถานะ + เรียก Gemini
    send_typing_action(chat_id, "typing")
    send_message(chat_id, f"🔎 กำลังค้นหาและสรุปข้อมูล <code>{_html_escape(query)}</code> ด้วย Gemini ครับ…", parse_mode="HTML")

    try:
        prompt = (
            "คุณคือผู้ช่วยค้นหาข่าวและข้อมูลอัปเดตจากเว็บแบบรวดเร็วและเชื่อถือได้ "
            "สรุปใจความสำคัญ กระชับ ชัดเจน เป็นภาษาไทย อ่านง่ายเป็นหัวข้อย่อย ถ้ามีตัวเลข/ราคา/วันที่ให้แสดงด้วย\n\n"
            f"หัวข้อ/คำค้น: {query}"
        )
        result = generate_text(prompt)
        _send_text_result(chat_id, query, result or "")
    except Exception as e:
        print(f"[handle_gemini_search] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาข้อมูล", parse_mode="HTML")

# =====================================================================
# 2) Image Generation (Signature ใหม่: รับ user_info)
# =====================================================================
def handle_gemini_image_generation(user_info: Dict[str, Any], user_text: str) -> None:
    chat_id = user_info["profile"]["user_id"]
    prompt = _normalize_query_for_image(user_text)

    if not prompt:
        send_message(
            chat_id,
            "❗️ วิธีใช้: <code>/image &lt;คำอธิบายภาพ&gt;</code>\n"
            "เช่น <code>/image นักบินอวกาศขี่ม้ายูนิคอร์นบนดาวอังคาร สไตล์พาสเทล</code>",
            parse_mode="HTML",
        )
        return

    send_typing_action(chat_id, "upload_photo")
    send_message(chat_id, f"🎨 กำลังสร้างสรรค์ภาพจากคำสั่ง: <code>{_html_escape(prompt)}</code>", parse_mode="HTML")

    try:
        # ขอไฟล์จาก Gemini
        path_or_err = generate_image_file(prompt)

        # ถ้า Gemini ส่ง error message (สตริงขึ้นต้นด้วย ❌ หรือว่าง)
        if not path_or_err or isinstance(path_or_err, str) and path_or_err.strip().startswith("❌"):
            err = path_or_err or "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ"
            send_message(chat_id, _html_escape(str(err)), parse_mode="HTML")
            return

        # รองรับทั้งกรณีที่คืน path โดยตรง หรือ (ในอนาคต) คืน path พร้อมนามสกุลอื่น
        file_path = str(path_or_err).strip()
        if not os.path.exists(file_path):
            send_message(chat_id, "❌ ไม่พบไฟล์ภาพที่สร้างขึ้นครับ", parse_mode="HTML")
            return

        # บังคับชื่อปลอดภัย (เปลี่ยนชื่อไฟล์ไปยัง tmp ชั่วคราวเพื่อกัน path แปลก)
        ext = os.path.splitext(file_path)[1].lower() or ".png"
        safe_tmp = _safe_temp_name(ext)
        try:
            # ย้ายไปชื่อปลอดภัยในโฟลเดอร์เดียวกัน
            base_dir = os.path.dirname(file_path) or "."
            safe_path = os.path.join(base_dir, safe_tmp)
            os.replace(file_path, safe_path)
        except Exception:
            # ถ้าย้ายไม่ได้ ใช้ path เดิม
            safe_path = file_path

        _send_image_file(chat_id, safe_path, caption=f"✨ ภาพจากจินตนาการ: {prompt}")

    except Exception as e:
        print(f"[handle_gemini_image_generation] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการสร้างภาพ", parse_mode="HTML")

# =====================================================================
# Legacy Signatures (รับ chat_id, user_text) — เผื่อโค้ดเก่ายังเรียก
# =====================================================================
def handle_gemini_search_legacy(chat_id: int | str, user_text: str) -> None:
    query = _normalize_query_for_search(user_text)
    if not query:
        send_message(chat_id, "❗️ พิมพ์ <code>/search &lt;คำค้น&gt;</code>", parse_mode="HTML")
        return
    send_typing_action(chat_id, "typing")
    send_message(chat_id, f"🔎 กำลังค้นหาและสรุปข้อมูล <code>{_html_escape(query)}</code> ด้วย Gemini ครับ…", parse_mode="HTML")
    try:
        prompt = (
            "สรุปข้อมูลล่าสุดจากเว็บให้เข้าใจง่าย เป็นหัวข้อย่อย ภาษาไทย และใส่ตัวเลข/วันที่สำคัญหากมี\n\n"
            f"หัวข้อ/คำค้น: {query}"
        )
        result = generate_text(prompt)
        _send_text_result(chat_id, query, result or "")
    except Exception as e:
        print(f"[handle_gemini_search_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการค้นหาข้อมูล", parse_mode="HTML")

def handle_gemini_image_generation_legacy(chat_id: int | str, user_text: str) -> None:
    prompt = _normalize_query_for_image(user_text)
    if not prompt:
        send_message(chat_id, "❗️ พิมพ์ <code>/image &lt;คำอธิบายภาพ&gt;</code>", parse_mode="HTML")
        return
    send_typing_action(chat_id, "upload_photo")
    send_message(chat_id, f"🎨 กำลังสร้างสรรค์ภาพจากคำสั่ง: <code>{_html_escape(prompt)}</code>", parse_mode="HTML")
    try:
        path_or_err = generate_image_file(prompt)
        if not path_or_err or (isinstance(path_or_err, str) and path_or_err.strip().startswith("❌")):
            err = path_or_err or "เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ"
            send_message(chat_id, _html_escape(str(err)), parse_mode="HTML")
            return

        file_path = str(path_or_err).strip()
        if not os.path.exists(file_path):
            send_message(chat_id, "❌ ไม่พบไฟล์ภาพที่สร้างขึ้นครับ", parse_mode="HTML")
            return

        ext = os.path.splitext(file_path)[1].lower() or ".png"
        safe_tmp = _safe_temp_name(ext)
        try:
            base_dir = os.path.dirname(file_path) or "."
            safe_path = os.path.join(base_dir, safe_tmp)
            os.replace(file_path, safe_path)
        except Exception:
            safe_path = file_path

        _send_image_file(chat_id, safe_path, caption=f"✨ ภาพจากจินตนาการ: {prompt}")
    except Exception as e:
        print(f"[handle_gemini_image_generation_legacy] ERROR: {e}")
        send_message(chat_id, "❌ ขออภัยครับ เกิดข้อผิดพลาดในการสร้างภาพ", parse_mode="HTML")
