from telegram import Update
from telegram.ext import ContextTypes
from serp_utils import get_lottery_result

async def lottery_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = get_lottery_result()
    await update.message.reply_text(reply)
