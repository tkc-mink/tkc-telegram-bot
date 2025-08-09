# main.py
# -*- coding: utf-8 -*-
import os
import sys
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, abort

from handlers.main_handler import handle_message
from utils.backup_utils import restore_all, setup_backup_scheduler
from settings import SUPPORTED_FORMATS

app = Flask(__name__)

# ---- Config / Env ----
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN", "").strip()
MAX_PAYLOAD_BYTES = int(os.getenv("MAX_PAYLOAD_BYTES", "10485760"))  # 10MB default

def log_event(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}", file=sys.stderr, flush=True)

# ======================
# Init: Restore & Schedule Backup
# ======================
def _safe_init():
    try:
        log_event("[INIT] Attempting restore all data from Google Drive...")
        restore_all()
        setup_backup_scheduler()
        log_event("[INIT] Auto restore + backup scheduler started")
    except Exception as e:
        log_event(f"[INIT ERROR] {e}\n{traceback.format_exc()}")

_safe_init()

# ======================
# Routes
# ======================
@app.route("/")
def index():
    return "✅ TKC Telegram Bot is running!"

@app.route("/healthz")
def healthz():
    # เอาไว้ให้ Render health checks
    return jsonify({"status": "healthy"}), 200

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/docs", methods=["GET"])
def docs():
    return jsonify({"supported_formats": SUPPORTED_FORMATS})

@app.route("/webhook", methods=["POST"])
def webhook():
    # 1) ตรวจ secret token (ถ้าตั้งไว้)
    if TELEGRAM_SECRET_TOKEN:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if got != TELEGRAM_SECRET_TOKEN:
            log_event("❌ Secret token mismatch on /webhook")
            abort(401)

    # 2) กัน payload ใหญ่เกิน
    raw = request.get_data(cache=False, as_text=False)
    if raw and len(raw) > MAX_PAYLOAD_BYTES:
        log_event(f"❌ Payload too large: {len(raw)} bytes")
        abort(413)

    # 3) parse JSON อย่างปลอดภัย
    data = None
    try:
        # Flask จะ parse ให้แล้วใน request.get_json แต่เราทำเองเพื่อจับ error ละเอียดขึ้น
        text = raw.decode("utf-8") if raw else ""
        data = json.loads(text) if text else (request.get_json(silent=True) or {})
    except Exception:
        # fallback
        data = request.get_json(silent=True) or {}

    try:
        log_event(f"Received webhook: {request.method} {request.path}")
        if data:
            # log เฉพาะบางส่วน กัน log ยาวเกิน
            snip = str(data)
            if len(snip) > 500:
                snip = snip[:500] + " ..."
            log_event(f"Telegram Data: {snip}")

            try:
                handle_message(data)  # ฟังก์ชันหลักจัดการ update จาก Telegram
            except Exception as e:
                log_event(f"❌ Handler error: {e}")
                log_event(traceback.format_exc())
        else:
            log_event("⚠️ No JSON data received from Telegram.")
    except Exception as e:
        log_event(f"❌ Webhook error: {e}")
        log_event(traceback.format_exc())

    return jsonify({"status": "ok"}), 200


# ---- Local dev only (บน Render ใช้ gunicorn/wsgi) ----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    log_event(f"Starting TKC Telegram Bot on port {port} (debug={debug_mode})")
    try:
        app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
    except KeyboardInterrupt:
        log_event("Received KeyboardInterrupt. Shutting down TKC Telegram Bot.")
