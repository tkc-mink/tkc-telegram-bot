import os
from flask import Flask, request
from handlers import handle_message

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    handle_message(data)
    return 'ok'

if __name__ == '__main__':
    app.run(port=5000)
