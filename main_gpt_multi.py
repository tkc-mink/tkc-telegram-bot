import os
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import openai
import asyncio

load_dotenv()

# --- Token & Webhook Config ---
TOKENS = {
    "shibanoy": os.getenv("BOT_TOKEN_SHIBANOY"),
    "giantjiw": os.getenv("BOT_TOKEN_GIANTJIW"),
    "p_tyretkc": os.getenv("BOT_TOKEN_P_TYRETKC"),
    "tex_speed": os.getenv("BOT_TOKEN_TEX_SPEED"),
}

openai.api_key = os.getenv("OPENAI_API_KEY")

# --- GPT Logic ---
async def ask_gpt(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "คุณคือผู้ช่วยอัจฉริยะของบริษัทกลุ่มตระกูลชัย ช่วยตอบคำถามในเชิงบวกและสร้างสรรค์"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"เกิดข้อผิดพลาดจาก GPT: {str(e)}"

# --- Message Handler ---
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    bot_name = context.bot.username.split('_')[1].lower()  # e.g., shibanoy, giantjiw

    if text.startswith("/"):
        await update.message.reply_text("🔧 คำสั่งนี้ยังไม่รองรับครับ")
        return

    reply = await ask_gpt(text)
    await update.message.reply_text(f"💬 GPT: {reply}")

    # --- Save log ต่อคน ---
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)
    user_log = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user.id,
        "username": user.username,
        "bot": bot_name,
        "question": text,
        "answer": reply
    }
    with open(f"{log_folder}/user_{user.id}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(user_log, ensure_ascii=False) + "\n")

# --- Init Bot ---
async def start_bot(name: str, token: str):
    print(f"🚀 Starting GPT bot: {name}")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    await app.initialize()
    await app.start()
    return app

async def main():
    apps = []
    for name, token in TOKENS.items():
        if token:
            apps.append(await start_bot(name, token))
        else:
            print(f"⚠️ No token for bot: {name}")
    print("✅ All GPT bots deployed.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
