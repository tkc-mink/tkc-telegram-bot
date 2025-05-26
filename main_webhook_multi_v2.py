import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)
import asyncio

load_dotenv()

TOKENS = {
    "shibanoy": {
        "token": os.getenv("BOT_TOKEN_SHIBANOY"),
        "url": os.getenv("WEBHOOK_URL_SHIBANOY"),
    },
    "giantjiw": {
        "token": os.getenv("BOT_TOKEN_GIANTJIW"),
        "url": os.getenv("WEBHOOK_URL_GIANTJIW"),
    },
    "p_tyretkc": {
        "token": os.getenv("BOT_TOKEN_P_TYRETKC"),
        "url": os.getenv("WEBHOOK_URL_P_TYRETKC"),
    },
    "tex_speed": {
        "token": os.getenv("BOT_TOKEN_TEX_SPEED"),
        "url": os.getenv("WEBHOOK_URL_TEX_SPEED"),
    },
}

async def start_bot(name, token, webhook_url):
    async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        await update.message.reply_text(f"[{name}] 📩 รับข้อความแล้ว: {text}")

    print(f"🚀 Starting bot: {name} at {webhook_url}")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    await app.initialize()
    await app.start()
    await app.bot.delete_webhook()  # สำคัญ: เคลียร์ของเดิมก่อน
    await app.bot.set_webhook(webhook_url)  # ตั้ง webhook ใหม่
    return app

async def main():
    apps = []
    for name, cfg in TOKENS.items():
        if cfg["token"] and cfg["url"]:
            apps.append(await start_bot(name, cfg["token"], cfg["url"]))
        else:
            print(f"⚠️ Skipped {name} (missing token or webhook URL)")
    print("✅ All bots deployed via webhook.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
