import os
import requests
from openai import OpenAI

# สร้าง client ของ OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def handle_message(data):
    try:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')

        # ส่งข้อความไปยัง GPT
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": text}
            ]
        )

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
