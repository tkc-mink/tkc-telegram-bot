# handlers/doc.py
# -*- coding: utf-8 -*-
"""
Handler for processing and summarizing uploaded documents.
Upgraded to integrate with the new user profile and memory system.
"""
from __future__ import annotations
import os
from typing import List, Tuple, Dict, Any

# --- ✅ ส่วนที่เราแก้ไข: จัดระเบียบ imports และใช้มาตรฐานใหม่ ---
from utils.telegram_api import send_message, send_chat_action
from utils.memory_store import append_message # <-- ใช้ memory_store ใหม่ของเรา
from utils.doc_extract_utils import (
    extract_text_pdf, extract_text_docx,
    extract_text_xlsx, extract_text_pptx
)
from utils.telegram_file_utils import download_telegram_file
from function_calling import summarize_text_with_gpt

# --- Configuration (คงไว้เหมือนเดิม) ---
_CHUNK_CHARS = int(os.getenv("DOC_SUMMARY_CHUNK_CHARS", "6000"))
_MAX_CHUNKS = int(os.getenv("DOC_SUMMARY_MAX_CHUNKS", "8"))
_MAX_FILE_MB = int(os.getenv("DOC_MAX_FILE_MB", "25"))
_SUPPORTED_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt"}

# --- Helper Functions (คงไว้เหมือนเดิม) ---
def _human_mb(n_bytes: int) -> float:
    try:
        return round(n_bytes / (1024 * 1024), 2)
    except Exception:
        return 0.0

def _split_text_smart(text: str, size: int) -> List[str]:
    # (โค้ดฟังก์ชันนี้เหมือนเดิมทุกประการ)
    text = (text or "").strip()
    if not text: return []
    paras = text.split("\n\n")
    chunks: List[str] = []
    buf: List[str] = []
    cur_len = 0
    for p in paras:
        p = p.strip()
        if not p: continue
        if len(p) > size:
            if buf:
                chunks.append("\n\n".join(buf).strip())
                buf, cur_len = [], 0
            for i in range(0, len(p), size):
                chunks.append(p[i:i+size])
            continue
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
    # (โค้ดฟังก์ชันนี้เหมือนเดิมทุกประการ)
    text = (full_text or "").strip()
    if not text: return "⚠️ ไม่พบข้อความในเอกสาร"
    if len(text) <= _CHUNK_CHARS:
        return summarize_text_with_gpt(text)
    chunks = _split_text_smart(text, _CHUNK_CHARS)[:_MAX_CHUNKS]
    if not chunks: return "⚠️ ไม่พบข้อมูลที่สรุปได้"
    partials = [
        summarize_text_with_gpt(f"[ตอนที่ {idx}/{len(chunks)}]\n{ck}")
        for idx, ck in enumerate(chunks, 1)
    ]
    merged = "\n\n".join(f"- {p}" for p in partials if p)
    final = summarize_text_with_gpt(
        "สรุปรวมประเด็นสำคัญทั้งหมดจากเนื้อหาต่อไปนี้ ให้กระชับ ชัดเจน และเข้าใจง่ายที่สุด:\n\n" + merged
    )
    return final

def _validate_document_meta(doc: dict) -> Tuple[bool, str]:
    # (โค้dฟังก์ชันนี้เหมือนเดิมทุกประการ)
    file_name = doc.get("file_name", "document")
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in _SUPPORTED_EXT:
        return False, "❌ รองรับเฉพาะไฟล์ PDF, Word, Excel, PowerPoint และ TXT ครับ"
    size = doc.get("file_size")
    if isinstance(size, int) and size > _MAX_FILE_MB * 1024 * 1024:
        mb = _human_mb(size)
        return False, f"❌ ไฟล์ใหญ่เกินไป ({mb} MB) จำกัดไม่เกิน {_MAX_FILE_MB} MB ครับ"
    return True, ""


# --- ✅ Entry Point ที่อัปเกรดแล้ว ---
def handle_doc(user_info: Dict[str, Any], msg: Dict[str, Any]) -> None:
    """
    รับไฟล์เอกสาร, ดาวน์โหลด, ดึงข้อความ, สรุป, และส่งกลับให้ผู้ใช้
    พร้อมบันทึกการกระทำลงในประวัติการสนทนาถาวร
    """
    # 1. ดึงข้อมูลที่จำเป็นจาก user_info
    chat_id = user_info['profile']['user_id']
    user_name = user_info['profile']['first_name']
    
    doc = msg.get("document") or {}
    if not doc:
        send_message(chat_id, "❌ ไม่พบไฟล์ที่แนบมาครับ")
        return

    ok, why = _validate_document_meta(doc)
    if not ok:
        send_message(chat_id, why)
        return

    file_name = doc.get("file_name", "document")
    file_id = doc.get("file_id")

    # 2. บันทึกการกระทำของผู้ใช้ลงในประวัติถาวร
    append_message(chat_id, "user", f"[อัปโหลดไฟล์: {file_name}]")
    
    # 3. แจ้งผู้ใช้ให้เป็นมิตรมากขึ้น
    send_chat_action(chat_id, "typing")
    send_message(chat_id, f"📥 ผมได้รับไฟล์ **{file_name}** ของคุณ {user_name} แล้วครับ\n\nกำลังเริ่มทำการสรุปให้ อาจใช้เวลาสักครู่ขึ้นอยู่กับขนาดของไฟล์นะครับ…")

    local_path = None
    try:
        local_path = download_telegram_file(file_id, file_name)
        if not local_path or not os.path.exists(local_path):
            send_message(chat_id, "❌ ขออภัยครับ ไม่สามารถดาวน์โหลดไฟล์จาก Telegram ได้ ลองใหม่อีกครั้งครับ")
            return

        # (ส่วนตรรกะการดึงข้อความเหมือนเดิม)
        ext = os.path.splitext(file_name)[1].lower()
        text = ""
        if ext == ".pdf": text = extract_text_pdf(local_path)
        elif ext == ".docx": text = extract_text_docx(local_path)
        elif ext == ".xlsx": text = "ข้อมูลใน Excel:\n" + extract_text_xlsx(local_path)
        elif ext == ".pptx": text = "ข้อมูลใน PowerPoint:\n" + extract_text_pptx(local_path)
        elif ext == ".txt":
            with open(local_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        
        text = (text or "").strip()
        if not text:
            send_message(chat_id, f"⚠️ **{file_name}** ไม่มีข้อความให้สรุปครับ")
            return

        # สรุปเนื้อหา
        send_chat_action(chat_id, "typing")
        summary = _hierarchical_summarize(text)
        
        # 4. ส่งสรุปและบันทึกคำตอบของบอทลงประวัติ
        final_message = f"📄 **สรุปใจความสำคัญจากไฟล์ {file_name} ครับ:**\n\n{summary}"
        send_message(chat_id, final_message, parse_mode="Markdown")
        append_message(chat_id, "assistant", final_message)

    except Exception as e:
        error_message = f"❌ ขออภัยครับคุณ {user_name} เกิดข้อผิดพลาดในการสรุปไฟล์: {e}"
        send_message(chat_id, error_message)
        append_message(chat_id, "assistant", error_message) # บันทึก error ลง history ด้วย
    finally:
        # ลบไฟล์ชั่วคราวเสมอ
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"[handle_doc] Failed to remove temp file {local_path}: {e}")
