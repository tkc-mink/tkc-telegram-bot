import os
import json
import requests
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# โหลด usage log
def load_usage():
    try:
        with open("usage_log.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# บันทึก usage log
def save_usage(data):
    with open("usage_log.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# บันทึก Log คำถาม-คำตอบ
def log_chat(user_id, text, reply):
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()
    log_folder = "chat_logs"
    os.makedirs(log_folder, exist_ok=True)
    log_path = os.path.join(log_folder, f"{today}.json")

    log_data = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []

    log_entry = {
        "user_id": user_id,
        "timestamp": timestamp,
        "message": text,
        "reply": reply
    }
    log_data.append(log_entry)

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

# จัดการข้อความที่เข้ามา
def handle_message(data):
    try:
        if "message" not in data or "text" not in data["message"]:
            return

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

        if usage[today][user_id] >= 30:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "ขออภัย คุณใช้ครบ 30 ครั้งแล้วในวันนี้"}
            )
            return

        # สร้าง system prompt
        system_prompt = (
            "คุณคือผู้ช่วยอัจฉริยะของพนักงานในองค์กรกลุ่มตระกูลชัย "
            "พูดจาสุภาพ ให้คำแนะนำกระชับ ตรงประเด็น และช่วยให้กำลังใจพนักงาน "
            "หากคำถามไม่ชัดเจนให้ถามกลับอย่างอ่อนโยน"
        )

        # ส่งคำถามไป GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            timeout=10,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )

        reply = response.choices[0].message.content.strip()

        # ส่งกลับ Telegram
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

        # อัปเดต usage + log
        usage[today][user_id] += 1
        save_usage(usage)
        log_chat(user_id, text, reply)

    except Exception as e:
        # แจ้ง error กลับ Telegram
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": data['message']['chat']['id'], "text": f"ระบบมีปัญหา: {str(e)}"}
        )
