# handlers.py

import os
import json
import re
import requests
from datetime import datetime
from openai import OpenAI
from search_utils import smart_search

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_USAGE_PER_DAY = 30

client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(chat_id, text):
    """ส่งข้อความธรรมดา"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )
    except Exception as e:
        print(f"[send_message] ERROR: {e}")

def send_photo(chat_id, photo_url, caption=None):
    """ส่งรูปภาพเข้าแชท Telegram"""
    try:
        data = {"chat_id": chat_id, "photo": photo_url}
        if caption:
            data["caption"] = caption
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json=data
        )
    except Exception as e:
        print(f"[send_photo] ERROR: {e}")

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

def is_image_url(url):
    return url.startswith("http") and any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"])

def handle_message(data):
    chat_id = None
    try:
        message = data.get("message", {})
        chat_id = message["chat"]["id"]
        user_id = str(chat_id)
        text = message.get("caption", "") or message.get("text", "")

        # -- Usage limit per user per day --
        today = datetime.now().strftime("%Y-%m-%d")
        usage = load_usage()
        usage.setdefault(today, {})
        usage[today].setdefault(user_id, 0)
        if usage[today][user_id] >= MAX_USAGE_PER_DAY:
            send_message(chat_id, f"ขออภัย คุณใช้งานครบ {MAX_USAGE_PER_DAY} ครั้งแล้วในวันนี้")
            return

        # -- ถ้าผู้ใช้ส่ง "รูปภาพ" ให้บอทวิเคราะห์รูป (Image-to-Text, GPT-4o) --
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

        # -- ถามเวอร์ชัน AI --
        if re.search(r"gpt-?4o", text, re.IGNORECASE):
            send_message(chat_id, "✅ ตอนนี้คุณกำลังคุยกับ GPT-4o (Omni) รุ่นใหม่ล่าสุดของ OpenAI พร้อมวิเคราะห์ข้อความและรูปภาพได้! ถามอะไรเพิ่มเติมได้เลยครับ 😊")
            usage[today][user_id] += 1
            save_usage(usage)
            return

        # -- ค้นข้อมูลเว็บ/ข่าว/รูป/ฯลฯ อัตโนมัติทุกข้อความ --
        search_results = smart_search(text)
        images = []
        messages = []
        for r in search_results:
            if isinstance(r, str) and r.startswith("http"):
                images.append(r)
            else:
                messages.append(r)

        # -- ส่งข้อความอธิบายก่อน --
        if messages:
            send_message(chat_id, "\n\n".join(messages))

        # -- ส่งรูปภาพ (ทีละ 1-3 รูป) --
        for photo_url in images[:3]:
            send_photo(chat_id, photo_url)

        # -- ส่งต่อให้ GPT-4o (Prompt ประกอบด้วย [คำถาม user] + [web search สรุป/ข่าว] + [url รูป] ถ้ามี) --
        gpt_messages = [
            {"role": "system", "content":
                "คุณคือผู้ช่วย AI ที่ฉลาด วิเคราะห์คำถามจากทั้งข้อมูลในโมเดลและข้อมูลล่าสุดจากเว็บ/ข่าว/รูปภาพด้านล่างนี้ หากข้อมูลจากเว็บหรือข่าวขัดแย้งกับโมเดล ให้ยึดข้อมูลเว็บ/ข่าวเป็นหลัก"},
            {"role": "user", "content": f"คำถาม: {text}\n\nสรุปข้อมูลจากเว็บ/ข่าว/รูป (ถ้ามี):\n" + "\n".join(messages + images)}
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=gpt_messages,
            max_tokens=1024,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        send_message(chat_id, reply)

        usage[today][user_id] += 1
        save_usage(usage)

    except Exception as e:
        log_error(chat_id, e)
