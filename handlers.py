# handlers.py - TKC Assistant Bot Module

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import os
import json

# ตัวแปรเก็บการใช้งาน (ใน production ควรใช้ database แทน)
USAGE_LIMIT = 30
USAGE_FILE = "data/usage.json"

def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

def check_limit(user_id: str) -> bool:
    usage = load_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in usage:
        return True
    return usage[user_id].get(today, 0) < USAGE_LIMIT

def increment_usage(user_id: str):
    usage = load_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in usage:
        usage[user_id] = {}
    usage[user_id][today] = usage[user_id].get(today, 0) + 1
    save_usage(usage)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if not check_limit(user_id):
        await update.message.reply_text("คุณใช้ครบ 30 คำถามแล้วในวันนี้ กรุณารอวันถัดไปครับ")
        return

    user_message = update.message.text
    increment_usage(user_id)

    # ส่งข้อความไปยัง GPT
    reply = await ask_gpt(user_message)
    await update.message.reply_text(reply)

# ฟังก์ชันจำลองการเรียก GPT (ใน main.py จะใช้จริง)
async def ask_gpt(text: str) -> str:
    return f"นี่คือตัวอย่างคำตอบของ GPT ต่อ: “{text}”"
