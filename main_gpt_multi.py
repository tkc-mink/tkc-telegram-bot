import logging
import asyncio
import openai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
from config.tokens import BOT_TOKENS, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
logging.basicConfig(level=logging.INFO)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    chat_id = update.effective_chat.id

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_input}]
        )
        reply_text = response.choices[0].message.content
    except Exception as e:
        reply_text = f"เกิดข้อผิดพลาดในการเชื่อมต่อ GPT: {str(e)}"

    await context.bot.send_message(chat_id=chat_id, text=reply_text)

async def run_bot(bot_token: str):
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

async def main():
    tasks = [run_bot(token) for token in BOT_TOKENS.values()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
