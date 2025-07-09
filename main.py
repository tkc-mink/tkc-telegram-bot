import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN") or "7774250343:AAHgBfWaZHEkFNRJ4_IXHy15LbL-XVQZzBs"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("สวัสดีครับ! บอท TKC Assistant พร้อมใช้งานแล้ว 🎉")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("พิมพ์ /start เพื่อเริ่มต้น หรือพิมพ์ /help เพื่อดูคำสั่งที่ใช้ได้ครับ")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    print("✅ Bot is running... (TKC Assistant)")
    app.run_polling()
