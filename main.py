import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY
import openai

# ตั้งค่าการแสดง log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"รับคำสั่ง /start จากผู้ใช้: {update.effective_user.id}")
    await update.message.reply_text(f"สวัสดีจากบอท {context.bot.username} 🐶")

async def chatgpt_reply(text: str) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        logger.info(f"ส่งข้อความไปยัง OpenAI: {text}")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        reply = response['choices'][0]['message']['content'].strip()
        logger.info(f"ได้รับคำตอบจาก OpenAI: {reply}")
        return reply
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาดจาก OpenAI: {e}")
        return f"เกิดข้อผิดพลาด: {e}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    logger.info(f"รับข้อความจากผู้ใช้ {update.effective_user.id}: {user_message}")
    reply = await chatgpt_reply(user_message)
    await update.message.reply_text(reply)

async def main():
    for name, token in BOT_TOKENS.items():
        logger.info(f"กำลังเริ่มบอท: {name}")
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await app.initialize()
        logger.info(f"เริ่ม polling สำหรับบอท: {name}")
        await app.updater.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
