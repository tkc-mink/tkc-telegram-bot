import os
import json
import requests
from datetime import datetime
from openai import OpenAI

# สร้าง client ของ OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# โหลด usage log จากไฟล์
def load_usage():
    try:
        with open("usage_log.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

# บันทึก usage log ลงไฟล์
def save_usage(data):
    with open("usage_log.json", "w") as f:
        json.dump(data, f)

# จัดการข้อความที่เข้ามา
def handle_message(data):
    try:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        today = datetime.now().strftime("%Y-%m-%d")
        user_id = str(chat_id)

        usage = load_usage()

        if today not in usage:
            usage[today] = {}

        if user_id not in usage[today]:
            usage[today][user_id] = 0

        # เช็คเกิน 30 ครั้งต่อวัน
        if usage[today][user_id] >= 30:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "ขออภัย คุณใช้งาน 30 ครั้งแล้วในวันนี้"}
            )
            return

        # ส่งข้อความไป GPT
        response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": text}]
)

        # บันทึกการใช้งาน
        usage[today][user_id] += 1
        save_usage(usage)

        # ส่งข้อความกลับ Telegram
        reply = response.choices[0].message.content.strip()
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    except Exception as e:
        # แจ้ง error กลับ Telegram
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"ระบบมีปัญหา: {str(e)}"}
        )
