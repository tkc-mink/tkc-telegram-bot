# handlers/doc.py
import os
from PyPDF2 import PdfReader

from utils.message_utils import send_message
from utils.history_utils import log_message
from utils.doc_extract_utils import (
    extract_text_pdf,
    extract_text_docx,
    extract_text_xlsx,
    extract_text_pptx,
)
from utils.telegram_file_utils import download_telegram_file
from function_calling import summarize_text_with_gpt  # ใช้ของเดิมคุณ

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

    # โหลดไฟล์
    local_path = download_telegram_file(file_id, file_name)
    if not local_path:
        send_message(chat_id, "❌ ไม่สามารถโหลดไฟล์ได้")
        return

    ext = os.path.splitext(file_name)[1].lower()
    try:
        if ext == ".pdf":
            text = extract_text_pdf(local_path)
        elif ext == ".docx":
            text = extract_text_docx(local_path)
        elif ext == ".xlsx":
            text = extract_text_xlsx(local_path)
            text = "ข้อมูลใน Excel:\n" + text
        elif ext == ".pptx":
            text = extract_text_pptx(local_path)
            text = "ข้อมูลใน PowerPoint:\n" + text
        elif ext == ".txt":
            with open(local_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            send_message(chat_id, "❌ รองรับเฉพาะ PDF, Word, Excel, PowerPoint, TXT เท่านั้น")
            return

        summary = summarize_text_with_gpt(text)
        send_message(chat_id, f"📄 สรุปไฟล์ {file_name} :\n{summary}")
        log_message(user_id, f"สรุปไฟล์ {file_name}", summary)

    except Exception as e:
        send_message(chat_id, f"❌ ไม่สามารถสรุปไฟล์: {e}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
