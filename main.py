from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from config.tokens import BOT_TOKENS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"สวัสดีจากบอท {context.bot.username} 🐶")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"คุณพิมพ์ว่า: {update.message.text}")

def get_bot_apps():
    apps = []
    for name, token in BOT_TOKENS.items():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        apps.append(app)
    return apps

import asyncio

async def main():
    bots = get_bot_apps()
    await asyncio.gather(*(app.initialize() or app.start() or app.updater.start_polling() for app in bots))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())