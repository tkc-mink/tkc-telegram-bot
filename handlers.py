import os
import requests
import openai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def handle_message(data):
    try:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')

        # ขอคำตอบจาก GPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # หรือ gpt-4 ก็ได้ถ้ามีสิทธิ์
            messages=[{"role": "user", "content": text}]
        )

        reply = response['choices'][0]['message']['content'].strip()

        # ส่งกลับ Telegram
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': reply}
        )
    except Exception as e:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            json={'chat_id': chat_id, 'text': f"ขออภัย ระบบมีปัญหา: {str(e)}"}
        )
