
import os
import logging
import openai
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

LOCAL_QUESTIONS = {
    "เฮียอยู่ไหน": "ขออภัย ระบบไม่สามารถให้ข้อมูลส่วนตัวได้นะครับ",
    "เบอร์ติดต่อ": "ขออภัย ระบบไม่สามารถให้ข้อมูลติดต่อบุคคลได้ครับ",
    "เหนื่อยจัง": "คุณเหนื่อยใช่ไหมครับ วันนี้ผมอยู่ตรงนี้เสมอครับ ✨",
}

USER_COMPANY = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USER_COMPANY[user.id] = "ยังไม่ระบุบริษัท"
    await update.message.reply_text(
        f"สวัสดีครับคุณ {user.first_name} 👋\n"
        "บอทนี้คือผู้ช่วยจากกลุ่มตระกูลชัย\n"
        "กรุณาพิมพ์ชื่อบริษัทของคุณ (เช่น: TKC, ไจแอนท์, ไพรม์ไทร์, สปีด)"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    if USER_COMPANY.get(user.id, "").startswith("ยังไม่"):
        USER_COMPANY[user.id] = text
        await update.message.reply_text(f"คุณสังกัดบริษัท: {text} แล้วครับ ✅")
        return

    for keyword in LOCAL_QUESTIONS:
        if keyword in text:
            await update.message.reply_text(LOCAL_QUESTIONS[keyword])
            return

    await update.message.reply_text("กำลังคิดคำตอบให้นะครับ 🤖...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"คุณคือบอทของบริษัท {USER_COMPANY.get(user.id, '')}"},
                {"role": "user", "content": text},
            ],
        )
        answer = response['choices'][0]['message']['content']
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"OpenAI Error: {e}")
        await update.message.reply_text("ขออภัย ระบบยังไม่สามารถตอบคำถามนี้ได้ในตอนนี้ครับ")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("บอทพร้อมทำงานแล้ว!")
    app.run_polling()

if __name__ == "__main__":
    main()
