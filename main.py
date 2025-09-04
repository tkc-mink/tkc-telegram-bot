# -*- coding: utf-8 -*-
import os
import sys
import json
import gzip
import traceback
from datetime import datetime
from typing import Any, Dict, Tuple

from flask import Flask, request, jsonify, abort, Response
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import RequestEntityTooLarge

# --- DB / Handlers / Settings ---
from utils.memory_store import init_db, _get_db_connection  # _get_db_connection ใช้ใน /healthz เชิงลึก
from handlers.main_handler import handle_message
from utils.backup_utils import restore_all, setup_backup_scheduler
try:
    from settings import SUPPORTED_FORMATS
except Exception:
    SUPPORTED_FORMATS = []

app = Flask(__name__)

# ---- Config / Env ----
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN", "").strip()
MAX_PAYLOAD_BYTES = int(os.getenv("MAX_PAYLOAD_BYTES", "10485760"))  # 10 MB
MAX_DECOMPRESSED_BYTES = int(os.getenv("MAX_DECOMPRESSED_BYTES", "20971520"))  # 20 MB ป้องกัน zip bomb
ENABLE_BACKUP_SCHEDULER = os.getenv("ENABLE_BACKUP_SCHEDULER", "1") == "1"
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "1") == "1"
LOG_JSON = os.getenv("LOG_JSON", "0") == "1"

if TRUST_PROXY_HEADERS:
    # ให้ Flask รู้จัก X-Forwarded-* จาก Render/Reverse proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ---- Logging ----
def _jsonlog(level: str, msg: str, **kw: Any) -> None:
    if LOG_JSON:
        payload = {"ts": datetime.utcnow().isoformat() + "Z", "level": level, "msg": msg}
        payload.update(kw)
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        extra = f" | {kw}" if kw else ""
        print(f"[{now}] [{level}] {msg}{extra}", file=sys.stderr, flush=True)

log_info = lambda m, **k: _jsonlog("INFO", m, **k)
log_warn = lambda m, **k: _jsonlog("WARN", m, **k)
log_err  = lambda m, **k: _jsonlog("ERROR", m, **k)

def _mask(i: Any) -> str:
    s = str(i)
    return s[:2] + "…" + s[-2:] if len(s) > 4 else "****"

def _read_update_json() -> Tuple[Dict[str, Any], int]:
    """
    อ่าน body อย่างปลอดภัย:
    - ตรวจ secret token
    - ลิมิตขนาด
    - รองรับ gzip (Content-Encoding: gzip)
    - คืน (data, raw_len)
    """
    # 1) Secret token
    if TELEGRAM_SECRET_TOKEN:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if got != TELEGRAM_SECRET_TOKEN:
            log_warn("Secret token mismatch on /webhook", got=_mask(got))
            abort(401)

    # 2) Read raw safely
    raw = request.get_data(cache=False, as_text=False) or b""
    if len(raw) > MAX_PAYLOAD_BYTES:
        log_warn("Payload too large (compressed)", size=len(raw))
        abort(413)

    # 3) Decompress if needed
    enc = (request.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        try:
            decompressed = gzip.decompress(raw)
        except Exception as e:
            log_warn("Gzip decompress failed", err=str(e))
            abort(400)
        if len(decompressed) > MAX_DECOMPRESSED_BYTES:
            log_warn("Payload too large (decompressed)", size=len(decompressed))
            abort(413)
        text = decompressed.decode("utf-8", errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace")

    # 4) Parse JSON
    if not text:
        return {}, len(raw)
    try:
        return json.loads(text), len(raw)
    except Exception:
        # fallback
        data = request.get_json(silent=True) or {}
        return data, len(raw)

# ======================
# Init: DB, Restore & Schedule Backup
# ======================
def _safe_init():
    try:
        log_info("INIT: Initializing database…")
        init_db()

        # กรณีรันหลายอินสแตนซ์ ให้เปิด/ปิด scheduler ด้วย ENV
        if ENABLE_BACKUP_SCHEDULER:
            log_info("INIT: Attempting restore all data from Drive…")
            restore_all()
            setup_backup_scheduler()
            log_info("INIT: Auto restore + backup scheduler started")
        else:
            log_info("INIT: Backup scheduler disabled by ENV")
    except Exception as e:
        log_err("INIT ERROR", err=str(e), tb=traceback.format_exc())

_safe_init()

# ======================
# Error Handlers (ให้ตอบ JSON เสมอ)
# ======================
@app.errorhandler(401)
def _401(_e): return jsonify({"error": "unauthorized"}), 401

@app.errorhandler(413)
def _413(_e: RequestEntityTooLarge): return jsonify({"error": "payload too large"}), 413

@app.errorhandler(404)
def _404(_e): return jsonify({"error": "not found"}), 404

@app.errorhandler(405)
def _405(_e): return jsonify({"error": "method not allowed"}), 405

@app.errorhandler(500)
def _500(_e): return jsonify({"error": "internal server error"}), 500

# ======================
# Routes
# ======================
@app.get("/")
def index():
    return "✅ TKC Telegram Bot is running!"

@app.get("/healthz")
def healthz():
    # เฮลธ์เช็ก DB แบบเร็ว ๆ
    db = "ok"
    try:
        with _get_db_connection() as conn:
            conn.execute("SELECT 1")  # lightweight ping
    except Exception as e:
        db = f"error: {e}"
    return jsonify({"status": "healthy", "db": db}), 200

@app.get("/readyz")
def readyz():
    # Readiness: ตรวจของสำคัญ ๆ
    checks = {
        "db": "ok",
        "telegram_secret": bool(TELEGRAM_SECRET_TOKEN),
        "backup_scheduler": ENABLE_BACKUP_SCHEDULER,
    }
    try:
        with _get_db_connection() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        checks["db"] = f"error: {e}"
    code = 200 if checks["db"] == "ok" else 503
    return jsonify(checks), code

@app.get("/ping")
def ping():
    return "pong", 200

@app.get("/docs")
def docs():
    return jsonify({"supported_formats": SUPPORTED_FORMATS})

@app.post("/webhook")
def webhook():
    data, raw_len = _read_update_json()

    log_info("Webhook received", method=request.method, path=request.path, size=raw_len)

    if not data:
        log_warn("No JSON data received from Telegram")
        return jsonify({"status": "ok"}), 200

    # Log แบบปลอดภัย: โชว์แค่ update_id / chat_id mask
    try:
        upd_id = data.get("update_id")
        msg = data.get("message") or data.get("edited_message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        log_info("Update meta", update_id=upd_id, chat=_mask(chat_id))
    except Exception:
        pass

    # ส่งต่อให้ handler หลัก (ภายในมี dedupe อีกชั้น)
    try:
        handle_message(data)
    except Exception as e:
        log_err("Handler error", err=str(e), tb=traceback.format_exc())

    # ตอบ Telegram ทันทีเพื่อกัน retry
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    log_info(f"Starting TKC Telegram Bot on port {port}", debug=debug_mode)
    try:
        app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
    except KeyboardInterrupt:
        log_info("Received KeyboardInterrupt. Shutting down TKC Telegram Bot.")
