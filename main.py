from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from config.tokens import BOT_TOKENS
from telegram import Update
from telegram.ext import ContextTypes

# คำสั่งเริ่มต้นเมื่อพิมพ์ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"สวัสดีจากบอท {context.bot.username} 🐶")

# ตอบกลับข้อความทั่วไป
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"คุณพิมพ์ว่า: {update.message.text}")

# ฟังก์ชันรวมบอททั้งหมดจาก token
def get_bot_apps():
    apps = []
    for name, token in BOT_TOKENS.items():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        apps.append(app)
    return apps

# รันทั้งหมดแบบ async
import asyncio
async def main():
    bots = get_bot_apps()
    await asyncio.gather(*[app.initialize() or app.start() for app in bots])

# จุดเริ่มต้น
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
