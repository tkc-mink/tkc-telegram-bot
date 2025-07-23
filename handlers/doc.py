import os
from telegram import Update
from telegram.ext import ContextTypes
from function_calling import summarize_text_with_gpt
from history_utils import log_message
from PyPDF2 import PdfReader

async def document_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    file_id = doc.file_id
    user_id = update.effective_user.id

    # โหลดไฟล์จาก Telegram
    file = await context.bot.get_file(file_id)
    file_path = f"/tmp/{file_name}"
    await file.download_to_drive(file_path)
    
    ext = os.path.splitext(file_name)[1].lower()
    summary = ""
    try:
        if ext == ".pdf":
            text = extract_text_pdf(file_path)
            summary = summarize_text_with_gpt(text)
        elif ext == ".txt":
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            summary = summarize_text_with_gpt(text)
        elif ext == ".docx":
            text = extract_text_docx(file_path)
            summary = summarize_text_with_gpt(text)
        elif ext == ".xlsx":
            text = extract_text_xlsx(file_path)
            summary = summarize_text_with_gpt("ข้อมูลใน Excel:\n" + text)
        elif ext == ".pptx":
            text = extract_text_pptx(file_path)
            summary = summarize_text_with_gpt("ข้อมูลใน PowerPoint:\n" + text)
        else:
            await update.message.reply_text("❌ รองรับเฉพาะ PDF, Word, Excel, PowerPoint, TXT เท่านั้น")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ ไม่สามารถสรุปไฟล์: {e}")
        return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    await update.message.reply_text(f"📄 <b>สรุปไฟล์ {file_name} :</b>\n{summary}", parse_mode='HTML')
    log_message(user_id, f"สรุปไฟล์ {file_name}", summary)

def extract_text_pdf(file_path, max_pages=10):
    reader = PdfReader(file_path)
    text = ""
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            text += "\n(ตัดเหลือ 10 หน้าแรก)"
            break
        text += page.extract_text() or ""
    return text.strip()

def extract_text_docx(file_path):
    from docx import Document
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_xlsx(file_path):
    from openpyxl import load_workbook
    wb = load_workbook(file_path, read_only=True)
    text = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            line = " | ".join([str(cell) if cell is not None else "" for cell in row])
            text.append(line)
        text.append("----------")
    return "\n".join(text[:200])  # limit

def extract_text_pptx(file_path):
    from pptx import Presentation
    prs = Presentation(file_path)
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
        text.append("---")
    return "\n".join(text)
