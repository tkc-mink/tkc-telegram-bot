from telegram import Update
from telegram.ext import ContextTypes
from history_utils import log_message, get_user_history

async def favorite_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "❗️ พิมพ์คำถามที่คุณอยากบันทึกต่อจากคำสั่ง เช่น:\n/favorite_add วิธีตั้งศูนย์ล้อ"
        )
        return

    message = " ".join(context.args)
    log_message(user_id, message, type="favorite")
    await update.message.reply_text("⭐️ บันทึกคำถามโปรดของคุณเรียบร้อยแล้วครับ")

async def favorite_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logs = get_user_history(user_id, limit=10, type="favorite")
    if not logs:
        await update.message.reply_text("📭 คุณยังไม่มีคำถามโปรดเลยครับ")
        return
    text = "\n\n".join([
        f"⭐️ <b>{l['q']}</b>\n🗓️ {l['date']}"
        for l in logs
    ])
    await update.message.reply_text(
        f"📌 <b>รายการคำถามโปรดของคุณ:</b>\n\n{text}",
        parse_mode='HTML'
    )
