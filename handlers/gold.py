from telegram import Update
from telegram.ext import ContextTypes
from gold_utils import get_gold_price

async def gold_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = get_gold_price()
    await update.message.reply_text(reply)
