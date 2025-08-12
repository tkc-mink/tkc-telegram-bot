# handlers/doc.py
# -*- coding: utf-8 -*-
import os
from typing import List, Tuple

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
from function_calling import summarize_text_with_gpt  # ใช้ของเดิม (มี No-Echo แล้ว)

# ---------------- Env / Config ----------------
# ขนาดก้อนสรุป (ตัวอักษร) — ประมาณ 2–3k tokens ต่อก้อน
_CHUNK_CHARS = int(os.getenv("DOC_SUMMARY_CHUNK_CHARS", "6000"))
# จำกัดจำนวนก้อนสูงสุด เพื่อคุมเวลาและโควตา
_MAX_CHUNKS  = int(os.getenv("DOC_SUMMARY_MAX_CHUNKS", "8"))
# จำกัดขนาดไฟล์ (MB)
_MAX_FILE_MB = int(os.getenv("DOC_MAX_FILE_MB", "25"))

_SUPPORTED_EXT = {".pdf", ".docx", ".xlsx", ".pptx", ".txt"}


# ---------------- Helpers ----------------
def _human_mb(n_bytes: int) -> float:
    try:
        return round(n_bytes / (1024 * 1024), 2)
    except Exception:
        return 0.0

def _split_text_smart(text: str, size: int) -> List[str]:
    """
    แบ่งข้อความเป็นก้อน ๆ โดยพยายาม 'ไม่ตัดกลางย่อหน้า/ประโยค'
    ขั้นตอน:
      1) ตัดด้วย "\n\n" (ย่อหน้า)
      2) สะสมย่อหน้าจนใกล้ size แล้วค่อยเปิดก้อนใหม่
      3) ย่อหน้าที่ยาวเกิน size จะถูก fallback เป็นการตัดแบบตรง ๆ เพื่อไม่ให้ตกหล่น
    """
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
            # ย่อหน้ามหึมา: บังคับตัดตรง ๆ
            if buf:
                chunks.append("\n\n".join(buf).strip())
                buf, cur_len = [], 0
            for i in range(0, len(p), size):
                chunks.append(p[i:i+size])
            continue

        # ถ้าเติมแล้วเกิน size -> ปิดก้อนเดิมก่อน
        if cur_len + len(p) + (2 if buf else 0) > size:
            if buf:
                chunks.append("\n\n".join(buf).strip())
            buf, cur_len = [p], len(p)
        else:
            buf.append(p)
            cur_len += len(p) + (2 if buf else 0)

    if buf:
        chunks.append("\n\n".join(buf).strip())

    return chunks


def _hierarchical_summarize(full_text: str) -> str:
    """
    ถ้าข้อความยาว: สรุปย่อยเป็นตอน ๆ ก่อน แล้วรวมสรุปอีกชั้น
    ถ้าสั้น: สรุปครั้งเดียว
    """
    text = (full_text or "").strip()
    if not text:
        return "⚠️ ไม่พบข้อความในเอกสาร"

    if len(text) <= _CHUNK_CHARS:
        return summarize_text_with_gpt(text)

    chunks = _split_text_smart(text, _CHUNK_CHARS)
    if not chunks:
        return "⚠️ ไม่พบข้อมูลที่สรุปได้"

    # จำกัดจำนวนก้อนสูงสุด
    chunks = chunks[:_MAX_CHUNKS]

    partials: List[str] = []
    total = len(chunks)
    for idx, ck in enumerate(chunks, 1):
        # ใส่หัวเพื่อให้โมเดลเข้าใจว่าคือส่วนที่เท่าไร
        partial = summarize_text_with_gpt(f"[ตอนที่ {idx}/{total}]\n{ck}")
        partials.append(partial)

    merged = "\n\n".join(f"- {p}" for p in partials if p)
    final = summarize_text_with_gpt(
        "สรุปรวมแบบ bullet ให้กระชับ ชัดเจน ภาษาไทย อ่านง่ายสำหรับผู้บริหาร:\n" + merged
    )
    return final


def _validate_document_meta(doc: dict) -> Tuple[bool, str]:
    # ตรวจสอบชนิดไฟล์และขนาดตาม metadata ที่ Telegram ส่งมา
    file_name = doc.get("file_name", "document")
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in _SUPPORTED_EXT:
        return False, "❌ รองรับเฉพาะ PDF, Word (docx), Excel (xlsx), PowerPoint (pptx), และ TXT"

    # บางครั้ง Telegram จะให้ file_size มาด้วย (ถ้าไม่มีจะข้าม)
    size = doc.get("file_size")
    if isinstance(size, int) and size > 0:
        mb = _human_mb(size)
        if mb > _MAX_FILE_MB:
            return False, f"❌ ไฟล์ใหญ่เกินไป ({mb} MB) — จำกัดไม่เกินประมาณ {_MAX_FILE_MB} MB"

    return True, ""


# ---------------- Entry ----------------
def handle_doc(chat_id, msg):
    """
    รับไฟล์จาก Telegram แล้วสรุป (PDF, DOCX, XLSX, PPTX, TXT)
    """
    doc = msg.get("document") or {}
    if not doc:
        send_message(chat_id, "❌ ไม่พบไฟล์ที่แนบมา")
        return

    ok, why = _validate_document_meta(doc)
    if not ok:
        send_message(chat_id, why)
        return

    file_name = doc.get("file_name", "document")
    file_id = doc.get("file_id")
    user_id = str(chat_id)

    # แจ้งผู้ใช้ว่ากำลังประมวลผล
    try:
        send_chat_action(chat_id, "typing")  # แสดงสถานะกำลังประมวลผล
    except Exception:
        pass
    send_message(chat_id, f"📥 รับไฟล์ **{file_name}** แล้ว กำลังสรุปให้ครับ อาจใช้เวลาสักครู่…")

    local_path = None
    try:
        # โหลดไฟล์จาก Telegram
        local_path = download_telegram_file(file_id, file_name)
        if not local_path or not os.path.exists(local_path):
            send_message(chat_id, "❌ ไม่สามารถดาวน์โหลดไฟล์ได้ ลองใหม่อีกครั้งครับ")
            return

        # ตรวจสอบขนาดจริงหลังดาวน์โหลด (เผื่อ metadata ไม่ตรง)
        real_mb = _human_mb(os.path.getsize(local_path))
        if real_mb > _MAX_FILE_MB:
            send_message(chat_id, f"❌ ไฟล์ใหญ่เกินไป ({real_mb} MB) — จำกัดไม่เกินประมาณ {_MAX_FILE_MB} MB")
            return

        ext = os.path.splitext(file_name)[1].lower()

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

        # สรุป (รองรับไฟล์ยาวด้วยการแบ่งตอนอย่างฉลาด)
        summary = _hierarchical_summarize(text)

        send_message(chat_id, f"📄 สรุปไฟล์ **{file_name}**\n\n{summary}")
        log_message(user_id, f"สรุปไฟล์ {file_name}", summary)

    except Exception as e:
        send_message(chat_id, f"❌ สรุปไฟล์ไม่สำเร็จ: {e}")
    finally:
        # ลบไฟล์ชั่วคราวเสมอ
        try:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
        except Exception:
            pass
