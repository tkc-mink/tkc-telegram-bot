from flask import Flask, request
import requests
import os

app = Flask(__name__)

# --- ตั้งค่า Bot ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- หน้าหลัก ใช้ตรวจสอบสถานะว่าเว็บขึ้นแล้ว ---
@app.route('/')
def index():
    return '✅ TKC Telegram Bot is running.', 200

# --- Route สำหรับ Telegram Webhook ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if not data or 'message' not in data:
        return 'no message', 200

    # ดึงข้อความและ chat_id
    message = data['message']
    chat_id = message['chat']['id']
    user_text = message.get('text', '')

    # กำหนดข้อความตอบกลับ
    reply = f"คุณพิมพ์ว่า: {user_text}"

    # ส่งกลับไปยังผู้ใช้
    send_message(chat_id, reply)

    return 'ok', 200

# --- ฟังก์ชันส่งข้อความกลับผู้ใช้ ---
def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

# --- รันแอป (กรณีทดสอบ local) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
