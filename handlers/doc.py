from telegram import Update
from telegram.ext import ContextTypes
from function_calling import summarize_text_with_gpt
from history_utils import log_message

async def document_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    # ใช้วิธี download ไฟล์ doc, call summarize_text_with_gpt ตาม logic เดิมคุณ
    # ตัวอย่างนี้ไม่แสดงเต็ม (ใช้แนวทางในโค้ดเดิม)
    await update.message.reply_text(f"ยังไม่เปิดใช้ฟีเจอร์นี้")
