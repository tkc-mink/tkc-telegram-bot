import os
import requests
from openai import OpenAI
from datetime import datetime
from search_utils import smart_search
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def handle_message(data):
    try:
        message = data.get("message", {})
        chat_id = message["chat"]["id"]
        text = message.get("caption", "") or message.get("text", "")

        # เช็กว่าเป็นภาพไหม
        if "photo" in message:
            # เอาไฟล์ใหญ่สุด (อันสุดท้าย)
            file_id = message["photo"][-1]["file_id"]
            file_info = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
            ).json()

            file_path = file_info["result"]["file_path"]
            image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
            
            # ตรวจสอบว่าเป็นข้อความค้นหาหรือไม่
if re.search(r"(ขอลิงก์|ค้นหา|หาข้อมูล|แหล่งข้อมูล|เว็บไซต์|เว็บ)", text):
    results = smart_search(text)
    if results:
        reply = "🔎 ผมค้นหาข้อมูลให้แล้วครับ:\n" + "\n\n".join(results)
    else:
        reply = "ขออภัย ผมไม่พบลิงก์ที่เกี่ยวข้องครับ"

    # ส่งกลับแล้วออกจากฟังก์ชัน
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )
    return

            # ส่งรูป + คำอธิบายไป GPT-4o
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            },
                            {
                                "type": "text",
                                "text": text or "ช่วยวิเคราะห์ภาพนี้ให้หน่อย"
                            }
                        ]
                    }
                ]
            )

            reply = response.choices[0].message.content.strip()

        else:
            # ถ้าไม่ใช่ภาพ → ใช้ flow เดิม
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
                    json={"chat_id": chat_id, "text": "ขออภัย คุณใช้งาน 30 ครั้งแล้วในวันนี้"}
                )
                return
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": text}]
            )
            reply = response.choices[0].message.content.strip()
            usage[today][user_id] += 1
            save_usage(usage)

        # ส่งข้อความกลับ
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    except Exception as e:
        # แจ้ง error
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"❌ ระบบมีปัญหา: {str(e)}"}
        )
