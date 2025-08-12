# handlers/doc.py
# -*- coding: utf-8 -*-
import os
from typing import List

from utils.message_utils import send_message
from utils.history_utils import log_message
from utils.doc_extract_utils import (
    extract_text_pdf,
    extract_text_docx,
    extract_text_xlsx,
    extract_text_pptx,
)
from utils.telegram_file_utils import download_telegram_file
from utils.telegram_api import send_chat_action  # แจ้งสถานะใน Telegram
from function_calling import summarize_text_with_gpt  # ใช้ของเดิมคุณ

# ตั้งค่า chunk สรุปทีละก้อน (ประมาณ ~2-3k tokens/ก้อน)
_CHUNK_CHARS = int(os.getenv("DOC_SUMMARY_CHUNK_CHARS", "6000"))
_MAX_CHUNKS  = int(os.getenv("DOC_SUMMARY_MAX_CHUNKS", "8"))  # กันไม่ให้สรุปยาวเกินเหตุ


def _split_text(text: str, size: int) -> List[str]:
    """ตัดข้อความเป็นก้อน ๆ ตามจำนวนอักขระที่กำหนด (ตัดแบบไม่ซอยคำซับซ้อน)"""
    text = text.strip()
    return [text[i:i+size] for i in range(0, len(text), size)]


def _hierarchical_summarize(full_text: str) -> str:
    """
    ถ้าข้อความยาว: สรุปย่อยเป็นตอน ๆ ก่อน แล้วรวมสรุปอีกชั้น
    ถ้าสั้น: สรุปครั้งเดียว
    """
    if len(full_text) <= _CHUNK_CHARS:
        return summarize_text_with_gpt(full_text)

    chunks = _split_text(full_text, _CHUNK_CHARS)[:_MAX_CHUNKS]
    partials: List[str] = []
    for idx, ck in enumerate(chunks, 1):
        partials.append(summarize_text_with_gpt(f"[ตอนที่ {idx}/{len(chunks)}]\n{ck}"))

    merged = "\n\n".join(f"- {p}" for p in partials)
    final = summarize_text_with_gpt("สรุปรวมจากสรุปย่อยเหล่านี้ ให้กระชับ ชัดเจน ภาษาไทย:\n" + merged)
    return final


def handle_doc(chat_id, msg):
    """
    รับไฟล์จาก Telegram แล้วสรุป (PDF, DOCX, XLSX, PPTX, TXT)
    """
    doc = msg.get("document") or {}
    if not doc:
        send_message(chat_id, "❌ ไม่พบไฟล์ที่แนบมา")
        return

    file_name = doc.get("file_name", "document")
    file_id = doc.get("file_id")
    user_id = str(chat_id)

    # แจ้งผู้ใช้ว่ากำลังประมวลผล
    try:
        send_chat_action(chat_id, "upload_document")  # แสดงสถานะใน Telegram
    except Exception:
        pass
    send_message(chat_id, f"📥 รับไฟล์ **{file_name}** แล้ว กำลังสรุปให้ครับ อาจใช้เวลาสักครู่…")

    # โหลดไฟล์จาก Telegram
    local_path = download_telegram_file(file_id, file_name)
    if not local_path:
        send_message(chat_id, "❌ ไม่สามารถดาวน์โหลดไฟล์ได้ ลองใหม่อีกครั้งครับ")
        return

    ext = os.path.splitext(file_name)[1].lower()
    try:
        # ดึงข้อความจากไฟล์ตามชนิด
        if ext == ".pdf":
            text = extract_text_pdf(local_path)
        elif ext == ".docx":
            text = extract_text_docx(local_path)
        elif ext == ".xlsx":
            text = "ข้อมูลใน Excel:\n" + extract_text_xlsx(local_path)
        elif ext == ".pptx":
            text = "ข้อมูลใน PowerPoint:\n" + extract_text_pptx(local_path)
        elif ext == ".txt":
            with open(local_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            send_message(chat_id, "❌ รองรับเฉพาะ PDF, Word (docx), Excel (xlsx), PowerPoint (pptx), และ TXT")
            return

        text = (text or "").strip()
        if not text:
            send_message(chat_id, "⚠️ ไฟล์นี้ไม่มีข้อความให้สรุปครับ")
            return

        # สรุป (รองรับไฟล์ยาวด้วยการแบ่งตอน)
        summary = _hierarchical_summarize(text)

        send_message(chat_id, f"📄 สรุปไฟล์ **{file_name}**\n\n{summary}")
        log_message(user_id, f"สรุปไฟล์ {file_name}", summary)

    except Exception as e:
        send_message(chat_id, f"❌ สรุปไฟล์ไม่สำเร็จ: {e}")
    finally:
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass
