from telegram import Update
from telegram.ext import ContextTypes
from serp_utils import get_stock_info

async def stock_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("ตัวอย่าง: /stock PTT")
        return
    symbol = args[0]
    reply = get_stock_info(symbol)
    await update.message.reply_text(reply)
