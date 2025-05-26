import os
import asyncio
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from config.tokens import BOT_TOKENS, OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def ask_gpt(message: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "คุณคือผู้ช่วยที่สุภาพและให้คำตอบอย่างกระชับ"},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"เกิดข้อผิดพลาดขณะเรียก GPT: {str(e)}"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    reply = await ask_gpt(user_message)
    await update.message.reply_text(reply)

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_URL")

async def run_bot(token, bot_name):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print(f"✅ Starting GPT bot: {bot_name}")
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"{WEBHOOK_BASE_URL}/{token}",
        secret_token=token
    )

async def main():
    print("🚀 Initializing all GPT bots...")
    tasks = []
    for bot_name, token in BOT_TOKENS.items():
        print(f"▶️ Launching bot: {bot_name}")
        tasks.append(asyncio.create_task(run_bot(token, bot_name)))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
