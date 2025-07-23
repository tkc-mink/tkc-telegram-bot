from telegram import Update
from telegram.ext import ContextTypes
from search_utils import robust_image_search
from history_utils import log_message

async def image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if not text:
        await update.message.reply_text("พิมพ์สิ่งที่ต้องการค้นหาภาพ เช่น 'ขอรูปรถกระบะ'")
        return
    imgs = robust_image_search(text)
    if imgs:
        for url in imgs[:3]:
            await update.message.reply_photo(url, caption=f"ผลลัพธ์: {text}")
    else:
        await update.message.reply_text(f"ไม่พบภาพสำหรับ '{text}'")
    log_message(user_id, text, "ส่งรูปภาพ (ดูในแชท)")
