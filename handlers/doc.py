# handlers/doc.py
# -*- coding: utf-8 -*-
"""
Handler for processing and summarizing uploaded documents.
Stable + safe version, integrated with new memory system.
"""
from __future__ import annotations
import os
from typing import List, Tuple, Dict, Any

# ✅ ใช้ wrapper ที่เสถียร (มี retry/แบ่งข้อความ/กัน no-echo)
from utils.message_utils import send_message, send_typing_action
from utils.memory_store import append_message
from utils.doc_extract_utils import (
    extract_text_pdf, extract_text_docx,
    extract_text_xlsx, extract_text_pptx
)
from utils.telegram_file_utils import download_telegram_file
from function_calling import summarize_text_with_gpt

# --- Configuration ---
_CHUNK_CHARS = int(os.getenv("DOC_SUMMARY_CHUNK_CHARS", "6000"))
_MAX_CHUNKS   = int(os.getenv("DOC_SUMMARY_MAX_CHUNKS", "8"))
_MAX_FILE_MB  = int(os.getenv("DOC_MAX_FILE_MB", "25"))
_SUPPORTED_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt"}

# Limit ความยาวที่บันทึกลง memory (กัน context โตเกิน)
_MEMORY_SAVE_LIMIT = int(os.getenv("DOC_MEMORY_SAVE_LIMIT", "4000"))

# --- Helpers ---
def _human_mb(n_bytes: int) -> float:
    try:
        return round(n_bytes / (1024 * 1024), 2)
    except Exception:
        return 0.0

def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _split_text_smart(text: str, size: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    paras = text.split("\n\n")
    chunks: List[str] = []
    buf: List[str] = []
    cur_len = 0
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(p) > size:
            if buf:
                chunks.append("\n\n".join(buf).strip())
                buf, cur_len = [], 0
            # ตัดพารากราฟยาวเป็นท่อน ๆ
            for i in range(0, len(p), size):
                chunks.append(p[i:i + size])
            continue
        # ปิดก้อนเดิมเมื่อจะล้น
        if cur_len + len(p) + (2 if buf else 0) > size:
            if buf:
                chunks.append("\n\n".join(buf).strip())
            buf, cur_len = [p], len(p)
        else:
            buf.append(p)
            cur_len += len(p) + (2 if len(buf) > 1 else 0)
    if buf:
        chunks.append("\n\n".join(buf).strip())
    return chunks

def _hierarchical_summarize(full_text: str) -> str:
    text = (full_text or "").strip()
    if not text:
        return "⚠️ ไม่พบข้อความในเอกสาร"
    if len(text) <= _CHUNK_CHARS:
        return summarize_text_with_gpt(text) or ""
    chunks = _split_text_smart(text, _CHUNK_CHARS)[:_MAX_CHUNKS]
    if not chunks:
        return "⚠️ ไม่พบข้อมูลที่สรุปได้"
    partials = [
        summarize_text_with_gpt(f"[ตอนที่ {idx}/{len(chunks)}]\n{ck}") or ""
        for idx, ck in enumerate(chunks, 1)
    ]
    merged = "\n\n".join(f"- {p.strip()}" for p in partials if p.strip())
    final = summarize_text_with_gpt(
        "สรุปรวมประเด็นสำคัญทั้งหมดจากเนื้อหาต่อไปนี้ ให้กระชับ ชัดเจน และเข้าใจง่ายที่สุด:\n\n" + merged
    ) or ""
    return final.strip() or "⚠️ ไม่สามารถสรุปเนื้อหาได้"

def _validate_document_meta(doc: dict) -> Tuple[bool, str]:
    file_name = doc.get("file_name", "document")
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in _SUPPORTED_EXT:
        return False, "❌ รองรับเฉพาะไฟล์ PDF, Word, Excel, PowerPoint และ TXT ครับ"
    size = doc.get("file_size")
    if isinstance(size, int) and size > _MAX_FILE_MB * 1024 * 1024:
        mb = _human_mb(size)
        return False, f"❌ ไฟล์ใหญ่เกินไป ({mb} MB) จำกัดไม่เกิน {_MAX_FILE_MB} MB ครับ"
    return True, ""

# --- Entry Point ---
def handle_doc(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """
    รับไฟล์เอกสาร, ดาวน์โหลด, ดึงข้อความ, สรุป, ส่งกลับ และบันทึกลง memory
    - ใช้ parse_mode=HTML เสมอ (escape ข้อความผู้ใช้แล้ว)
    - ลบไฟล์ชั่วคราวท้ายงานเสมอ
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    doc = msg.get("document") or {}
    if not doc:
        send_message(chat_id, "❌ ไม่พบไฟล์ที่แนบมาครับ")
        return

    ok, why = _validate_document_meta(doc)
    if not ok:
        send_message(chat_id, _html_escape(why))
        return

    raw_name = doc.get("file_name", "document")
    safe_name = os.path.basename(raw_name)  # กัน path traversal
    file_id = doc.get("file_id")
    size_mb = _human_mb(doc.get("file_size") or 0)

    # บันทึกการกระทำของผู้ใช้ลงในประวัติถาวร
    append_message(chat_id, "user", f"[อัปโหลดไฟล์: {safe_name}]")

    # แจ้งสถานะผู้ใช้
    send_typing_action(chat_id, "typing")
    send_message(
        chat_id,
        f"📥 ผมได้รับไฟล์ <code>{_html_escape(safe_name)}</code> ของคุณ {_html_escape(user_name)} แล้วครับ "
        f"(~{size_mb} MB)\nกำลังเริ่มทำการสรุปให้ อาจใช้เวลาสักครู่ขึ้นอยู่กับขนาดของไฟล์นะครับ…",
        parse_mode="HTML",
    )

    local_path = None
    try:
        local_path = download_telegram_file(file_id, safe_name)
        if not local_path or not os.path.exists(local_path):
            send_message(chat_id, "❌ ขออภัยครับ ไม่สามารถดาวน์โหลดไฟล์จาก Telegram ได้ ลองใหม่อีกครั้งครับ")
            return

        # ดึงข้อความจากไฟล์
        ext = os.path.splitext(safe_name)[1].lower()
        text = ""
        if ext == ".pdf":
            text = extract_text_pdf(local_path)
        elif ext == ".docx":
            text = extract_text_docx(local_path)
        elif ext == ".xlsx":
            text = "ข้อมูลใน Excel:\n" + (extract_text_xlsx(local_path) or "")
        elif ext == ".pptx":
            text = "ข้อมูลใน PowerPoint:\n" + (extract_text_pptx(local_path) or "")
        elif ext == ".txt":
            with open(local_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()

        text = (text or "").strip()
        if not text:
            send_message(chat_id, f"⚠️ ไฟล์ <code>{_html_escape(safe_name)}</code> ไม่มีข้อความให้สรุปครับ", parse_mode="HTML")
            return

        # สรุปเนื้อหา (hierarchical)
        send_typing_action(chat_id, "typing")
        summary = _hierarchical_summarize(text)

        # ส่งสรุป
        final_message = f"📄 <b>สรุปใจความสำคัญจากไฟล์</b> <code>{_html_escape(safe_name)}</code>\n\n{_html_escape(summary)}"
        send_message(chat_id, final_message, parse_mode="HTML")

        # บันทึกคำตอบของบอทลงประวัติ (จำกัดความยาว)
        to_save = final_message if len(final_message) <= _MEMORY_SAVE_LIMIT else (final_message[:_MEMORY_SAVE_LIMIT] + " …")
        append_message(chat_id, "assistant", to_save)

    except Exception as e:
        err = _html_escape(str(e))
        error_message = f"❌ ขออภัยครับคุณ {_html_escape(user_name)} เกิดข้อผิดพลาดในการสรุปไฟล์: <code>{err}</code>"
        send_message(chat_id, error_message, parse_mode="HTML")
        append_message(chat_id, "assistant", error_message)
    finally:
        # ลบไฟล์ชั่วคราวเสมอ
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"[handle_doc] Failed to remove temp file {local_path}: {e}")
