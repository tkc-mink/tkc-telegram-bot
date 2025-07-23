# handlers/lottery.py

from telegram import Update
from telegram.ext import ContextTypes
from serp_utils import get_lottery_result

async def lottery_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ตอบผลสลากกินแบ่งรัฐบาลล่าสุด (ดึงจาก serp_utils)
    """
    try:
        reply = get_lottery_result()
        if not reply or len(reply.strip()) < 10:
            await update.message.reply_text("❌ ไม่สามารถดึงข้อมูลผลหวยได้ในขณะนี้")
        else:
            await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("❌ เกิดข้อผิดพลาดขณะดึงผลสลากกินแบ่ง")
        print(f"[lottery_result] {e}")
