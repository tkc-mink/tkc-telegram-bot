from telegram import Update
from telegram.ext import ContextTypes
from history_utils import get_user_history

async def my_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logs = get_user_history(user_id, limit=10)
    if not logs:
        await update.message.reply_text("🔍 คุณยังไม่มีประวัติการใช้งานเลยครับ")
        return
    text = "\n\n".join([
        f"🗓️ <b>{l['date']}</b>\n❓{l['q']}\n{'💬 '+l['a'] if 'a' in l else ''}"
        for l in logs
    ])
    await update.message.reply_text(
        f"📜 <b>ประวัติคำถามย้อนหลัง:</b>\n\n{text}",
        parse_mode='HTML'
    )

