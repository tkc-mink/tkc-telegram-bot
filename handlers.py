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

        # --- เช็ค limit การใช้งาน ---
        today = datetime.now().strftime("%Y-%m-%d")
        usage = load_usage()
        usage.setdefault(today, {})
        usage[today].setdefault(user_id, 0)

        if usage[today][user_id] >= MAX_USAGE_PER_DAY:
            send_message(chat_id, f"ขออภัย คุณใช้งานครบ {MAX_USAGE_PER_DAY} ครั้งแล้วในวันนี้")
            return

        # --- วิเคราะห์รูปภาพด้วย GPT-4o ---
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

        # --- Web Search ทุกข้อความ & ส่งเข้า GPT-4o ---
        # 1. หาผลลัพธ์จากเว็บ (smart_search)
        search_results = smart_search(text)
        web_summary = "\n".join(search_results[:3]) if search_results else "ไม่พบข้อมูลสดจากเว็บ"

        # 2. สร้าง prompt รวม: [ข้อความผู้ใช้] + [ผลสรุปจากเว็บล่าสุด]
        system_prompt = (
            "คุณคือแชตบอทที่วิเคราะห์ข้อมูลแบบ AI สามารถใช้ทั้งความรู้จากโมเดลและข้อมูลสดล่าสุดจากเว็บ "
            "หากข้อมูลจากเว็บล่าสุดมีความสำคัญ ให้ใช้ประกอบการตอบเสมอ"
        )
        gpt_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"คำถาม: {text}\n\nข้อมูลล่าสุดจากเว็บ:\n{web_summary}"}
        ]

        # ถามว่าใช้ GPT-4o ไหม — ตอบแน่ชัด
        if re.search(r"gpt-?4o", text, re.IGNORECASE):
            send_message(chat_id, "ใช่ครับ ตอนนี้คุณกำลังคุยกับ GPT-4o (Omni) เวอร์ชันล่าสุดของ OpenAI สามารถวิเคราะห์ทั้งข้อความและข้อมูลสดจากเว็บได้ทันทีครับ!")
            usage[today][user_id] += 1
            save_usage(usage)
            return

        # 3. ส่งเข้า GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=gpt_prompt,
            max_tokens=1024,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        send_message(chat_id, reply)
        usage[today][user_id] += 1
        save_usage(usage)

    except Exception as e:
        log_error(chat_id, e)
