import os
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, abort
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
        # -- Security: Check if Telegram only (Optional) --
        # if request.headers.get("User-Agent", "").startswith("TelegramBot"):
        #     pass
        # else:
        #     log_event("⚠️ Forbidden request source")
        #     abort(403)
        
        # -- Logging --
        log_event(f"Received webhook: {request.method} {request.path}")
        # For extra debug:
        # log_event(f"Headers: {dict(request.headers)}")
        data = request.get_json(force=True, silent=True)
        if data:
            log_event(f"Telegram Data: {str(data)[:300]}")
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

# Optional: OCR/Document Test endpoint (internal use only)
@app.route('/docs', methods=['GET'])
def docs():
    return jsonify({"supported_formats": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".jpg", ".png"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = bool(os.environ.get("FLASK_DEBUG", "0") == "1")
    log_event(f"Starting TKC Telegram Bot on port {port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
