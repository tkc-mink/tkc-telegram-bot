from telegram.ext import ApplicationBuilder, CommandHandler
from config.tokens import BOT_TOKENS

from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"สวัสดีจากบอท {context.bot.username} 👋")

def get_bot_apps():
    apps = []
    for name, token in BOT_TOKENS.items():
        app = ApplicationBuilder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        apps.append(app)
    return apps

import asyncio
async def main():
    bots = get_bot_apps()
    await asyncio.gather(*[app.initialize() or app.start() or app.updater.start_polling() for app in bots])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
