import os
from flask import Flask, request
from handlers import handle_message

app = Flask(__name__)

@app.route('/')
def index():
    return 'bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        handle_message(data)
    except Exception as e:
        print(f"Webhook error: {e}")
    return 'ok', 200
