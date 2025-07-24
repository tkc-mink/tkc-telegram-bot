from telegram import Update
from telegram.ext import ContextTypes
from utils.favorite_utils import add_favorite, get_favorites, remove_favorite

async def favorite_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "❗️ พิมพ์ข้อความที่คุณอยากบันทึกต่อจากคำสั่ง เช่น:\n"
            "/favorite_add วิธีตั้งศูนย์ล้อ"
        )
        return
    message = " ".join(context.args).strip()
    if not message:
        await update.message.reply_text("❗️ กรุณาระบุข้อความที่ต้องการบันทึก")
        return
    ok = add_favorite(user_id, message)
    if ok:
        await update.message.reply_text("⭐️ บันทึกคำถามโปรดเรียบร้อยแล้วครับ")
    else:
        await update.message.reply_text("📌 ข้อความนี้มีอยู่ในรายการโปรดของคุณแล้ว")

async def favorite_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    favs = get_favorites(user_id, limit=10)
    if not favs:
        await update.message.reply_text("📭 คุณยังไม่มีคำถามโปรดเลยครับ")
        return
    text = "\n\n".join([
        f"⭐️ <b>{item['q']}</b>\n🗓️ {item['date']}" for item in favs
    ])
    await update.message.reply_text(
        f"📌 <b>รายการคำถามโปรดของคุณ:</b>\n\n{text}",
        parse_mode='HTML'
    )

async def favorite_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❗️ ระบุข้อความที่ต้องการลบ เช่น\n/favorite_remove ข้อความ")
        return
    question = " ".join(context.args).strip()
    if not question:
        await update.message.reply_text("❗️ กรุณาระบุข้อความที่ต้องการลบ")
        return
    ok = remove_favorite(user_id, question)
    if ok:
        await update.message.reply_text("🗑️ ลบคำถามโปรดเรียบร้อยแล้วครับ")
    else:
        await update.message.reply_text("ไม่พบรายการนี้ในคำถามโปรดของคุณ")
