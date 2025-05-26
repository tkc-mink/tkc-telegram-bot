
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY
import openai

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"สวัสดีจากบอท {context.bot.username} 🐶")

async def chatgpt_reply(text: str) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": text}]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return f"เกิดข้อผิดพลาดจากระบบ: {e}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    reply = await chatgpt_reply(user_message)
    await update.message.reply_text(reply)

async def main():
    bots = []
    for name, token in BOT_TOKENS.items():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        bots.append(app)

    await asyncio.gather(*[app.initialize() or app.start() or app.updater.start_polling() for app in bots])

if __name__ == "__main__":
    asyncio.run(main())
