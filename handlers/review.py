from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from review_utils import set_review, need_review_today

ASK_REVIEW = 1

async def ask_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if need_review_today(user_id):
        await update.message.reply_text("❓ กรุณารีวิวความพึงพอใจการใช้บอทวันนี้ (1-5):")
        return ASK_REVIEW
    else:
        await update.message.reply_text("วันนี้ไม่จำเป็นต้องรีวิวครับ")
        return ConversationHandler.END

async def receive_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rating = update.message.text.strip()
    if rating not in ["1", "2", "3", "4", "5"]:
        await update.message.reply_text("กรุณาตอบเป็นตัวเลข 1-5 เท่านั้นครับ")
        return ASK_REVIEW
    set_review(user_id, int(rating))
    await update.message.reply_text("✅ ขอบคุณสำหรับรีวิวครับ!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ยกเลิกการรีวิว")
    return ConversationHandler.END
