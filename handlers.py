import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def handle_message(data):
    if 'message' not in data:
        return
    chat_id = data['message']['chat']['id']
    user_message = data['message'].get('text', '')

    if not user_message:
        return

    # ส่งข้อความไปยัง OpenAI
    gpt_response = ask_gpt(user_message)

    # ส่งข้อความกลับ Telegram
    send_telegram_message(chat_id, gpt_response)

def ask_gpt(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return "ขออภัย ระบบไม่สามารถตอบได้ในขณะนี้"

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)
