import os
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from handlers import handle_message

app = Flask(__name__)

def log_event(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", file=sys.stderr, flush=True)

@app.route('/')
def index():
    return '✅ TKC Telegram Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Log basic request info
        log_event(f"Received webhook: {request.method} {request.path}")
        # For extra debug, log headers only if needed
        # log_event(f"Headers: {dict(request.headers)}")
        data = request.get_json(force=True, silent=True)
        if data:
            log_event(f"Telegram Data: {str(data)[:256]}")
            handle_message(data)
        else:
            log_event("⚠️ No data received from Telegram.")
    except Exception as e:
        log_event(f"❌ Webhook error: {e}")
        log_event(traceback.format_exc())
    return jsonify({"status": "ok"}), 200

# Healthcheck route for uptime monitor
@app.route('/healthz')
def healthz():
    return jsonify({"status": "healthy"}), 200

# Optionally add CORS headers
# from flask_cors import CORS
# CORS(app)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = bool(os.environ.get("FLASK_DEBUG", "0") == "1")
    log_event(f"Starting TKC Telegram Bot on port {port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
