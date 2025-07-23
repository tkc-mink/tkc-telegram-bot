# handlers/doc.py

import os
import requests
from function_calling import summarize_text_with_gpt
from history_utils import log_message
from utils.message_utils import send_message
from PyPDF2 import PdfReader

def handle_doc(chat_id, msg):
    """
    สรุปไฟล์ที่ผู้ใช้ upload มาทาง Telegram (รองรับ PDF, Word, Excel, PowerPoint, TXT)
    msg: dict ที่ได้จาก telegram webhook
    """
    doc = msg.get("document", {})
    if not doc:
        send_message(chat_id, "❌ ไม่พบไฟล์ที่แนบมา")
        return
    file_name = doc.get("file_name", "document")
    file_id = doc.get("file_id")
    user_id = str(chat_id)

    # โหลดไฟล์จาก Telegram
    file_path = download_telegram_file(file_id, file_name)
    if not file_path:
        send_message(chat_id, "❌ ไม่สามารถโหลดไฟล์ได้ (getFile error)")
        return

    ext = os.path.splitext(file_name)[1].lower()
    summary = ""
    try:
        if ext == ".pdf":
            text = extract_text_pdf(file_path)
            if not text:
                send_message(chat_id, "❌ ไม่สามารถอ่าน PDF ได้")
                return
            summary = summarize_text_with_gpt(text)
        elif ext == ".txt":
            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                summary = summarize_text_with_gpt(text)
            except Exception:
                send_message(chat_id, "❌ ไม่สามารถอ่าน TXT ได้")
                return
        elif ext == ".docx":
            text = extract_text_docx(file_path)
            if not text:
                send_message(chat_id, "❌ ไม่สามารถอ่าน Word ได้")
                return
            summary = summarize_text_with_gpt(text)
        elif ext == ".xlsx":
            text = extract_text_xlsx(file_path)
            if not text:
                send_message(chat_id, "❌ ไม่สามารถอ่าน Excel ได้")
                return
            summary = summarize_text_with_gpt("ข้อมูลใน Excel:\n" + text)
        elif ext == ".pptx":
            text = extract_text_pptx(file_path)
            if not text:
                send_message(chat_id, "❌ ไม่สามารถอ่าน PowerPoint ได้")
                return
            summary = summarize_text_with_gpt("ข้อมูลใน PowerPoint:\n" + text)
        else:
            send_message(chat_id, "❌ รองรับเฉพาะ PDF, Word, Excel, PowerPoint, TXT เท่านั้น")
            return
    except Exception as e:
        send_message(chat_id, f"❌ ไม่สามารถสรุปไฟล์: {e}")
        return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    send_message(chat_id, f"📄 สรุปไฟล์ {file_name} :\n{summary}")
    log_message(user_id, f"สรุปไฟล์ {file_name}", summary)

def download_telegram_file(file_id, file_name):
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10
        )
        r.raise_for_status()
        result = r.json().get("result")
        if not result or "file_path" not in result:
            return None
        file_path = result["file_path"]
        url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        local_path = f"/tmp/{file_name}"
        with requests.get(url, stream=True, timeout=20) as resp, open(local_path, "wb") as out:
            for chunk in resp.iter_content(chunk_size=8192):
                out.write(chunk)
        return local_path
    except Exception as e:
        print(f"[download_telegram_file] {e}")
        return None

def extract_text_pdf(file_path, max_pages=10):
    try:
        reader = PdfReader(file_path)
        text = ""
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                text += "\n(ตัดเหลือ 10 หน้าแรก)"
                break
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        print(f"[extract_text_pdf] {e}")
        return ""

def extract_text_docx(file_path):
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"[extract_text_docx] {e}")
        return ""

def extract_text_xlsx(file_path):
    try:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, read_only=True)
        text = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                line = " | ".join([str(cell) if cell is not None else "" for cell in row])
                text.append(line)
            text.append("----------")
        return "\n".join(text[:200])
    except Exception as e:
        print(f"[extract_text_xlsx] {e}")
        return ""

def extract_text_pptx(file_path):
    try:
        from pptx import Presentation
        prs = Presentation(file_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
            text.append("---")
        return "\n".join(text)
    except Exception as e:
        print(f"[extract_text_pptx] {e}")
        return ""
