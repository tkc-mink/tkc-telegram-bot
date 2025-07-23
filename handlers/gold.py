# handlers/gold.py

from telegram import Update
from telegram.ext import ContextTypes
from gold_utils import get_gold_price

async def gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ตอบราคาทองคำล่าสุด/วันนี้ให้ user
    """
    try:
        reply = get_gold_price()
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("❌ ไม่สามารถดึงราคาทองได้ในขณะนี้\nโปรดลองใหม่อีกครั้ง")
        print(f"[gold_price handler] ERROR: {e}")
