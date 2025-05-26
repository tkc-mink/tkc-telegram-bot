import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY
import openai

# Logging สำหรับ debug เต็ม
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"[{context.bot.username}] รับคำสั่ง /start จาก user_id: {user_id}")
    await update.message.reply_text(f"สวัสดีจาก {context.bot.username} 👋")

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
    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"[{context.bot.username}] ข้อความเข้าใหม่จาก user_id: {user_id} - ข้อความ: {user_message}")
    reply = await chatgpt_reply(user_message)
    await update.message.reply_text(reply)

async def main():
    bots = []
    for name, token in BOT_TOKENS.items():
        logger.info(f"กำลังเริ่มบอท: {name} | TOKEN: {token[:10]}... (ซ่อนบางส่วน)")
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await app.initialize()
        bots.append(app)

    # ใช้ start() แทน start_polling() สำหรับ PTB v20+
    await asyncio.gather(*[bot.start() for bot in bots])

if __name__ == "__main__":
    asyncio.run(main())
