from telegram import Update
from telegram.ext import ContextTypes
from serp_utils import get_crypto_price

async def crypto_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("ตัวอย่าง: /crypto BTC")
        return
    symbol = args[0]
    reply = get_crypto_price(symbol)
    await update.message.reply_text(reply)
