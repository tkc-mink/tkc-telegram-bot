import os
from flask import Flask, request
from handlers import handle_message

app = Flask(__name__)

@app.route('/')
def index():
    return '✅ TKC Telegram Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if data:
            handle_message(data)
        else:
            print("⚠️ No data received from Telegram.")
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return 'ok', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
