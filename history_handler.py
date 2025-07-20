# history_handler.py - TKC Assistant Bot Module

from telegram import Update
from telegram.ext import ContextTypes
import os
import json

HISTORY_FOLDER = "data/history"

def ensure_folder():
    if not os.path.exists(HISTORY_FOLDER):
        os.makedirs(HISTORY_FOLDER)

def get_history_file(user_id):
    return os.path.join(HISTORY_FOLDER, f"{user_id}.json")

def log_user_history(user_id, message, reply):
    ensure_folder()
    history_file = get_history_file(user_id)
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append({"question": message, "answer": reply})
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

async def handle_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    history_file = get_history_file(user_id)

    if not os.path.exists(history_file):
        await update.message.reply_text("คุณยังไม่มีประวัติการใช้งานครับ")
        return

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    MAX_ITEMS = 5
    display = history[-MAX_ITEMS:]  # แสดงรายการล่าสุด 5 รายการ
    message_lines = [f"{i+1}. ถาม: {item['question']}\n   ตอบ: {item['answer']}" for i, item in enumerate(display)]
    reply = "\n\n".join(message_lines)

    await update.message.reply_text(reply)
