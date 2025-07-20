import os
from datetime import datetime
import json
import requests
from openai import OpenAI

# สร้าง client ของ OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# โหลดจำนวนครั้งจากไฟล์
def load_usage():
    try:
        with open("usage_log.json", "r") as f:
            return json.load(f)
    except:
        return {}

# บันทึกจำนวนครั้งลงไฟล์
def save_usage(data):
    with open("usage_log.json", "w") as f:
        json.dump(data, f)

def handle_message(data):
    try:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        # ตรวจสอบจำนวนครั้งที่ถามวันนี้
usage = load_usage()
today = datetime.now().strftime("%Y-%m-%d")
user_id = str(chat_id)

if today not in usage:
    usage[today] = {}

if user_id not in usage[today]:
    usage[today][user_id] = 0

if usage[today][user_id] >= 30:
    requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        json={"chat_id": chat_id, "text": "ขออภัย คุณใช้ครบ 30 ครั้งแล้วในวันนี้"}
    )
    return


        # ส่งข้อความไปยัง GPT
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": text}
            ]
        )

usage[today][user_id] += 1
save_usage(usage)

        reply = response.choices[0].message.content.strip()

        # ส่งข้อความกลับไปยัง Telegram
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': reply}
        )

    except Exception as e:
        # ถ้า error ให้แจ้งกลับใน Telegram
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': f"ขออภัย ระบบเกิดปัญหา: {str(e)}"}
        )
