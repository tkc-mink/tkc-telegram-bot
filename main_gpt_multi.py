import os
import asyncio
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY
import openai

async def gpt_response(message: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❗ GPT Error: {str(e)}"

async def handle_message(update, context):
    user_message = update.message.text
    user_id = update.effective_user.id
    response = await gpt_response(user_message)
    await update.message.reply_text(f"💬 GPT: {response}")

async def start_bot(name, token):
    print(f"🚀 Starting GPT bot: {name}")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

async def main():
    tasks = []
    for name, token in BOT_TOKENS.items():
        if token:
            tasks.append(start_bot(name, token))
    if not tasks:
        print("❗ No bot tokens found.")
        return
    await asyncio.gather(*tasks)
    print("✅ All GPT bots deployed.")

if __name__ == "__main__":
    openai.api_key = OPENAI_API_KEY
    asyncio.run(main())
