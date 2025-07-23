from PyPDF2 import PdfReader

def extract_text_pdf(path, max_pages=10):
    reader = PdfReader(path)
    text = ""
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            text += "\n(ตัดเหลือ 10 หน้าแรก)"
            break
        text += page.extract_text() or ""
    return text.strip()

def extract_text_docx(path):
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True)
    lines = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            line = " | ".join([str(c) if c is not None else "" for c in row])
            lines.append(line)
        lines.append("----------")
    return "\n".join(lines[:200])

def extract_text_pptx(path):
    from pptx import Presentation
    prs = Presentation(path)
    lines = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                lines.append(shape.text)
        lines.append("---")
    return "\n".join(lines)
