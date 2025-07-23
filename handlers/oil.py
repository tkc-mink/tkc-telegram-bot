from telegram import Update
from telegram.ext import ContextTypes
from serp_utils import get_oil_price

async def oil_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = get_oil_price()
    await update.message.reply_text(reply)
