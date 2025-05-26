import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY
import openai

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
        return f"เกิดข้อผิดพลาด: {e}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    reply = await chatgpt_reply(user_message)
    await update.message.reply_text(reply)

async def main():
    for name, token in BOT_TOKENS.items():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        await app.initialize()
        await app.updater.start_polling()
        # NOTE: ไม่ใช้ await app.start() เพราะ Render ไม่รองรับ Webhook background

if __name__ == "__main__":
    asyncio.run(main())
