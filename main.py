import os
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, abort

from handlers import handle_message
from backup_utils import restore_all, setup_backup_scheduler  # <- เพิ่ม module backup

app = Flask(__name__)

def log_event(msg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] {msg}", file=sys.stderr, flush=True)

@app.before_first_request
def initialize():
    log_event("Attempting restore all data from Google Drive...")
    try:
        restore_all()  # Restore ข้อมูลสำคัญทุกครั้งที่บอท start (deploy ใหม่)
        setup_backup_scheduler()  # ตั้งเวลา backup ขึ้น Google Drive ทุกวัน 00:09 AM
        log_event("Auto restore + backup scheduler started")
    except Exception as e:
        log_event(f"[INIT ERROR] {e}\n{traceback.format_exc()}")

@app.route('/')
def index():
    return '✅ TKC Telegram Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        log_event(f"Received webhook: {request.method} {request.path}")
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

@app.route('/healthz')
def healthz():
    return jsonify({"status": "healthy"}), 200

@app.route('/docs', methods=['GET'])
def docs():
    return jsonify({"supported_formats": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".jpg", ".png"]})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    debug_mode = bool(os.environ.get("FLASK_DEBUG", "0") == "1")
    log_event(f"Starting TKC Telegram Bot on port {port} (debug={debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=debug_mode)
