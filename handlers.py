import os
import json
import re
import requests
from datetime import datetime
from openai import OpenAI
from search_utils import smart_search

# --------- ENV CONFIG ---------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_USAGE_PER_DAY = 30

client = OpenAI(api_key=OPENAI_API_KEY)

# --------- UTILITIES ---------
def send_message(chat_id, text):
    """ส่งข้อความไปยัง Telegram"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print(f"[send_message] ERROR: {e}")

def log_error(chat_id, e):
    print(f"[log_error] {e}")
    try:
        send_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")
    except Exception:
        pass

def load_usage():
    try:
        with open("usage.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_usage(data):
    try:
        with open("usage.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[save_usage] ERROR: {e}")

# --------- MAIN HANDLER ---------
def handle_message(data):
    chat_id = None
    try:
        message = data.get("message", {})
        chat_id = message["chat"]["id"]
        user_id = str(chat_id)
        text = message.get("caption", "") or message.get("text", "")

        # ตรวจสอบขีดจำกัดการใช้งาน
        today = datetime.now().strftime("%Y-%m-%d")
        usage = load_usage()
        usage.setdefault(today, {})
        usage[today].setdefault(user_id, 0)

        if usage[today][user_id] >= MAX_USAGE_PER_DAY:
            send_message(chat_id, f"ขออภัย คุณใช้งานครบ {MAX_USAGE_PER_DAY} ครั้งแล้วในวันนี้")
            return

        # ---------- 1. Smart Search ----------
        if re.search(r"(ขอลิงก์|ค้นหา|หาข้อมูล|แหล่งข้อมูล|เว็บไซต์|เว็บ)", text):
            results = smart_search(text)
            reply = "🔎 ค้นหาข้อมูลให้แล้วครับ:\n\n" + "\n\n".join(results)
            send_message(chat_id, reply)
            usage[today][user_id] += 1
            save_usage(usage)
            return

        # ---------- 2. วิเคราะห์รูปภาพ ----------
        if "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            file_info = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
            ).json()
            file_path = file_info["result"]["file_path"]
            image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": text or "ช่วยวิเคราะห์ภาพนี้ให้หน่อย"}
                        ]
                    }
                ]
            )
            reply = response.choices[0].message.content.strip()
            send_message(chat_id, reply)
            usage[today][user_id] += 1
            save_usage(usage)
            return

        # ---------- 3. ข้อความปกติ / Prompt ไป GPT-4o ----------
        # ถ้าผู้ใช้ถามว่า “คุณคือ GPT-4o ไหม” ให้ตอบเฉพาะ
        if re.search(r"gpt-?4o", text, re.IGNORECASE):
            send_message(chat_id, "ใช่ครับ ตอนนี้คุณกำลังคุยกับ GPT-4o (Omni) รุ่นใหม่ล่าสุดของ OpenAI พร้อมวิเคราะห์ข้อความและภาพได้! ถามอะไรเพิ่มเติมได้เลยครับ 😊")
            usage[today][user_id] += 1
            save_usage(usage)
            return

        # ปกติ: คุยกับ GPT-4o (ข้อความ)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": text}],
            max_tokens=1024,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        send_message(chat_id, reply)
        usage[today][user_id] += 1
        save_usage(usage)

    except Exception as e:
        log_error(chat_id, e)
