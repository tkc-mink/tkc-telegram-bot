import os
import requests
from openai import OpenAI  # ✅ SDK แบบใหม่

# ใช้ Client แบบใหม่
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def handle_message(data):
    try:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')

        # เรียก GPT แบบใหม่
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # หรือ gpt-4 ถ้ามีสิทธิ์
            messages=[{"role": "user", "content": text}]
        )

        reply = response.choices[0].message.content.strip()

        # ส่งกลับ Telegram
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': reply}
        )

    except Exception as e:
        # ส่ง error กลับ Telegram
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': f"ขออภัย ระบบมีปัญหา: {str(e)}"}
        )
