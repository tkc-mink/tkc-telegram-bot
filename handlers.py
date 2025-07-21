import os
import json
import re
import requests
from datetime import datetime
from openai import OpenAI
from search_utils import smart_search

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ---------- UTILITIES ----------

def send_message(chat_id, text):
    """ส่งข้อความไปยังผู้ใช้ Telegram"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print(f"[send_message] ERROR: {e}")

def log_error(chat_id, e):
    """ส่งข้อความแสดงข้อผิดพลาด"""
    print(f"[log_error] {e}")
    try:
        send_message(chat_id, f"❌ เกิดข้อผิดพลาด: {str(e)}")
    except:
        pass

def load_usage():
    try:
        with open("usage.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_usage(data):
    try:
        with open("usage.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[save_usage] ERROR: {e}")

# ---------- MAIN ----------

def handle_message(data):
    try:
        message = data.get("message", {})
        chat_id = message["chat"]["id"]
        user_id = str(chat_id)
        text = message.get("caption", "") or message.get("text", "")

        # 🔎 ตรวจสอบว่าเป็นคำค้นหาหรือไม่
        if re.search(r"(ขอลิงก์|ค้นหา|หาข้อมูล|แหล่งข้อมูล|เว็บไซต์|เว็บ)", text):
            results = smart_search(text)
            reply = "🔎 ผมค้นหาข้อมูลให้แล้วครับ:\n\n" + "\n\n".join(results)
            send_message(chat_id, reply)
            return

        # 🖼️ กรณีเป็นภาพ
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
            return

        # 💬 ข้อความทั่วไป
        today = datetime.now().strftime("%Y-%m-%d")
        usage = load_usage()
        usage.setdefault(today, {})
        usage[today].setdefault(user_id, 0)

        if usage[today][user_id] >= 30:
            send_message(chat_id, "ขออภัย คุณใช้งานครบ 30 ครั้งแล้วในวันนี้")
            return

        # ส่งข้อความไป GPT
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": text}]
        )
        reply = response.choices[0].message.content.strip()
        usage[today][user_id] += 1
        save_usage(usage)
        send_message(chat_id, reply)

    except Exception as e:
        log_error(chat_id, e)
