from flask import Flask, request

app = Flask(__name__)

@app.route('/')
def index():
    return "👋 TKC Assistant Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Received webhook data:", data)
    # คุณสามารถใส่โค้ดประมวลผลจาก Telegram ที่นี่
    return "OK", 200
