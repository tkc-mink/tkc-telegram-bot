import os
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify

from handlers.main_handler import handle_message
from backup_utils import restore_all, setup_backup_scheduler
from settings import SUPPORTED_FORMATS

app = Flask(__name__)

# === Restore & Schedule backup (one-time) ===
try:
    print("[INIT] Attempting restore all data from Google Drive...")
    restore_all()
    setup_backup_scheduler()
    print("[INIT] Auto restore + backup scheduler started")
except Exception as e:
    print(f"[INIT ERROR] {e}\n{traceback.format_exc()}")

def log_event(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", file=sys.stderr, flush=True)

@app.route('/')
def index():
    return '✅ TKC Telegram Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        log_event(f"Received webhook: {request.method} {request.path}")
        data = request.get_json(force=True, silent=True)
        if data:
            log_event(f"Telegram Data: {str(data)[:300]} ...")
            try:
                handle_message(data)
            except Exception as e:
                log_event(f"❌ Handler error: {e}")
                log_event(traceback.format_exc())
        else:
            log_event("⚠️ No data received from Telegram.")
    except Exception as e:
        log_event(f"❌ Webhook error: {e}")
        log_event(traceback.format_exc())
    return jsonify({"status": "ok"}), 200

@app.route('/healthz')
def healthz():
    return jsonify({"status": "healthy"}), 200

@app.route('/docs', methods=['GET'])
def docs():
    return jsonify({"supported_formats": SUPPORTED_FORMATS})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = bool(os.environ.get("FLASK_DEBUG", "0") == "1")
    log_event(f"Starting TKC Telegram Bot on port {port} (debug={debug_mode})")
    try:
        app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
    except KeyboardInterrupt:
        log_event("Received KeyboardInterrupt. Shutting down TKC Telegram Bot.")
