from telegram import Update
from telegram.ext import ContextTypes
from weather_utils import get_weather_forecast

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # สมมติว่าดึง lat/lon จากระบบ location ที่คุณมี
    # ตัวอย่างนี้ assume มี location เดิมใน DB
    from history_utils import get_user_location
    loc = get_user_location(user_id)
    if loc and loc.get("lat") and loc.get("lon"):
        reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("กรุณาส่งตำแหน่งก่อนใช้คำสั่งนี้")
