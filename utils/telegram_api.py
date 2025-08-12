# utils/telegram_api.py
# -*- coding: utf-8 -*-
import os
import requests

# รองรับทั้ง TELEGRAM_BOT_TOKEN และ TELEGRAM_TOKEN
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or ""
)
API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

def send_message(chat_id, text, reply_markup=None):
    if not BOT_TOKEN:
        print("[telegram_api] Missing TELEGRAM_BOT_TOKEN/TELEGRAM_TOKEN")
        return None
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{API}/sendMessage", json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print("[telegram_api] send_message error:", e)

def answer_callback_query(callback_query_id, text=None):
    if not BOT_TOKEN or not callback_query_id:
        return
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        requests.post(f"{API}/answerCallbackQuery", json=payload, timeout=10)
    except Exception as e:
        print("[telegram_api] answer_callback_query error:", e)
