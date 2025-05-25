from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("สวัสดีจากน้องสปีด TKC 👋")

async def reply_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "สวัสดี" in text:
        await update.message.reply_text("น้องสปีด TKC ขอส่งยิ้มกลับครับ 😊")
    elif "รายงาน" in text:
        await update.message.reply_text("พิมพ์ /report เพื่อขอรายงานได้ในอนาคตนะครับ")
    elif "ช่วย" in text or "ขอความช่วยเหลือ" in text:
        await update.message.reply_text("น้องสปีด TKC พร้อมช่วยเหลือครับ หากต้องการคำสั่งอื่น ๆ พิมพ์ /help ได้เลยครับ")
    else:
        await update.message.reply_text("ขอบคุณที่ส่งข้อความมานะครับ 😊 (จาก น้องสปีด TKC)")
