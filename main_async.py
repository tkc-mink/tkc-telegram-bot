import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

BOT_TOKENS = {
    'shibanoy': os.getenv("BOT_TOKEN_SHIBANOY"),
    'giantjiw': os.getenv("BOT_TOKEN_GIANTJIW"),
    'p_tyretkc': os.getenv("BOT_TOKEN_P_TYRETKC"),
    'tex_speed': os.getenv("BOT_TOKEN_TEX_SPEED"),
}

async def create_bot(name, token):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        await update.message.reply_text(f"[{name}] 📨 รับข้อความแล้ว: {text}")

    print(f"🚀 Starting bot: {name}")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    return app

async def main():
    bots = []
    for name, token in BOT_TOKENS.items():
        if token:
            bots.append(await create_bot(name, token))
        else:
            print(f"⚠️ Token missing for: {name}")

    print("✅ All available bots are running.")
    # Keep running forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
