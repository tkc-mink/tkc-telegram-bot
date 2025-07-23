# handlers/image.py

from telegram import Update
from telegram.ext import ContextTypes
from search_utils import robust_image_search
from history_utils import log_message

async def image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ฟีเจอร์ค้นหารูปภาพจาก keyword (รองรับ: ขอรูป/ขอภาพ/image/photo)
    """
    user_id = update.effective_user.id
    text = update.message.text
    if not text or not any(k in text.lower() for k in ["ขอรูป", "ขอภาพ", "image", "photo"]):
        await update.message.reply_text("🖼️ กรุณาพิมพ์สิ่งที่ต้องการค้นหาภาพ เช่น 'ขอรูปรถกระบะ', 'ขอภาพแมว'")
        return

    # แยก keyword ที่ต้องการค้นหาจริงๆ (เช่น "ขอรูปรถกระบะ" → "รถกระบะ")
    keyword = (
        text.replace("ขอรูป", "")
            .replace("ขอภาพ", "")
            .replace("image", "")
            .replace("photo", "")
            .strip()
    )
    if not keyword:
        keyword = text  # fallback ถ้าตัดแล้วว่าง

    imgs = robust_image_search(keyword)
    if imgs:
        for url in imgs[:3]:  # ส่งได้สูงสุด 3 รูป
            await update.message.reply_photo(url, caption=f"ผลลัพธ์: {keyword}")
    else:
        await update.message.reply_text(f"ไม่พบภาพสำหรับ '{keyword}'")
    log_message(user_id, text, f"ค้นหารูปภาพ: {keyword}")
