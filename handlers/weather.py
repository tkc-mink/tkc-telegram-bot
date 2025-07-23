# handlers/weather.py

from telegram import Update
from telegram.ext import ContextTypes
from weather_utils import get_weather_forecast
from history_utils import get_user_location

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ตอบสภาพอากาศตามตำแหน่งล่าสุดของ user ถ้ามี location ในระบบ
    """
    user_id = update.effective_user.id
    loc = get_user_location(user_id)
    if loc and loc.get("lat") and loc.get("lon"):
        try:
            reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text("❌ ไม่สามารถดึงข้อมูลอากาศได้ในขณะนี้")
            print(f"[weather handler] ERROR: {e}")
    else:
        await update.message.reply_text("กรุณาส่งตำแหน่งของคุณก่อนใช้คำสั่งนี้\nพิมพ์ /share_location หรือกดปุ่มแชร์ location ในแชท")
