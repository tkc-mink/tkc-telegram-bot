# app.py (หรือ main.py)
# -*- coding: utf-8 -*-
import os
import sys
import io
import json
import gzip
import hmac
import uuid
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, Tuple

from flask import Flask, request, jsonify, abort
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import RequestEntityTooLarge

# --- Config (ศูนย์กลางทั้งหมด) ---
from config import (
    TELEGRAM_SECRET_TOKEN,
    MAX_PAYLOAD_BYTES,
    MAX_DECOMPRESSED_BYTES,
    ENABLE_BACKUP_SCHEDULER,
    TRUST_PROXY_HEADERS,
    LOG_JSON,
    OPENAI_KEY_SET,
    GOOGLE_KEY_SET,
    ROUTER_MODE,
    ROUTER_MIN_CONFIDENCE,
    OPENAI_MODEL_DIALOGUE,
    GEMINI_MODEL_DIALOGUE,
    GIT_SHA,
    BUILD_TIME,
    diag as config_diag,
    missing_required,
    missing_recommended,
)

# --- DB / Handlers / Settings ---
from utils.memory_store import init_db, _get_db_connection  # _get_db_connection ใช้ใน /healthz เชิงลึก
from handlers.main_handler import handle_message
from utils.backup_utils import restore_all, setup_backup_scheduler
try:
    from settings import SUPPORTED_FORMATS
except Exception:
    SUPPORTED_FORMATS = []

app = Flask(__name__)
# ตัด payload ตั้งแต่ชั้น WSGI (compressed length)
app.config['MAX_CONTENT_LENGTH'] = MAX_PAYLOAD_BYTES

# ---- Proxy / Trust headers ----
if TRUST_PROXY_HEADERS:
    # อ่านจำนวน proxy ชั้นนอกจาก ENV (ดีฟอลต์ 1)
    x_for    = int(os.getenv("PROXY_COUNT_X_FOR", "1") or 1)
    x_proto  = int(os.getenv("PROXY_COUNT_X_PROTO", "1") or 1)
    x_host   = int(os.getenv("PROXY_COUNT_X_HOST", "1") or 1)
    x_prefix = int(os.getenv("PROXY_COUNT_X_PREFIX", "1") or 1)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto, x_host=x_host, x_prefix=x_prefix)

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

# ---- Early guards (ก่อนอ่าน body แพง ๆ) ----
@app.before_request
def _early_guards():
    # enforce POST ที่ /webhook
    if request.path == "/webhook" and request.method != "POST":
        return jsonify({"error": "method not allowed"}), 405

def _read_update_json() -> Tuple[Dict[str, Any], int]:
    """
    อ่าน body อย่างปลอดภัย:
    - ตรวจ secret token (constant-time)
    - ลิมิตขนาด (compressed/decompressed)
    - รองรับ gzip (stream)
    - คืน (data, raw_len)
    """
    # 0) Trace id ต่อ request (ช่วยตาม log ง่าย)
    req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.environ["TKC_REQ_ID"] = req_id

    # 1) Secret token (constant-time compare)
    if TELEGRAM_SECRET_TOKEN:
        got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(got, TELEGRAM_SECRET_TOKEN):
            log_warn("Secret token mismatch on /webhook", req_id=req_id, got=_mask(got))
            abort(401)

    # 2) Read raw safely (compressed size already capped by MAX_CONTENT_LENGTH)
    raw = request.get_data(cache=False, as_text=False) or b""
    if len(raw) > MAX_PAYLOAD_BYTES:
        log_warn("Payload too large (compressed)", req_id=req_id, size=len(raw))
        abort(413)

    # 3) Decompress if needed (stream) + cap decompressed bytes
    enc = (request.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        try:
            buf = io.BytesIO(raw)
            gz = gzip.GzipFile(fileobj=buf, mode="rb")
            chunks = []
            total = 0
            CHUNK = 64 * 1024
            while True:
                piece = gz.read(CHUNK)
                if not piece:
                    break
                total += len(piece)
                if total > MAX_DECOMPRESSED_BYTES:
                    log_warn("Payload too large (decompressed)", req_id=req_id, size=total)
                    abort(413)
                chunks.append(piece)
            text = b"".join(chunks).decode("utf-8", errors="replace")
        except Exception as e:
            log_warn("Gzip decompress failed", req_id=req_id, err=str(e))
            abort(400)
    else:
        text = raw.decode("utf-8", errors="replace")

    # 4) Parse JSON
    if not text:
        return {}, len(raw)
    try:
        return json.loads(text), len(raw)
    except Exception:
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
            def _bg():
                try:
                    log_info("INIT: Attempting restore all data from Drive…")
                    restore_all()
                    setup_backup_scheduler()
                    log_info("INIT: Auto restore + backup scheduler started")
                except Exception as e:
                    log_err("INIT RESTORE/SCHED ERROR", err=str(e), tb=traceback.format_exc())
            threading.Thread(target=_bg, name="restore+backup", daemon=True).start()
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

@app.get("/version")
def version():
    return jsonify({
        "app": "tkc-telegram-bot",
        "git_sha": GIT_SHA or None,
        "build_time": BUILD_TIME or None,
        "models": {
            "openai_model": OPENAI_MODEL_DIALOGUE,
            "gemini_model": GEMINI_MODEL_DIALOGUE,
        },
        "router": {
            "mode": ROUTER_MODE,
            "min_confidence": ROUTER_MIN_CONFIDENCE,
        },
    }), 200

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
        "openai_key_set": OPENAI_KEY_SET,
        "google_key_set": GOOGLE_KEY_SET,
        "router_mode": ROUTER_MODE,
        "missing_required": missing_required(),
        "missing_recommended": missing_recommended(),
    }
    try:
        with _get_db_connection() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        checks["db"] = f"error: {e}"

    # พร้อมจริงต้อง DB ok และไม่มี missing_required
    ready = (checks["db"] == "ok") and not checks["missing_required"]
    return jsonify(checks), (200 if ready else 503)

@app.get("/diag")
def diag():
    """
    Deep diagnostics:
    - ใช้ config.diag() เป็นหลัก (มาตรฐานเดียว)
    - เช็ก import orchestrator/providers เพิ่มเติม (ไม่เรียก API ภายนอก)
    """
    payload = config_diag()

    imports = {}
    try:
        import orchestrator  # noqa: F401
        imports["orchestrator"] = True
    except Exception as e:
        imports["orchestrator"] = False
        imports["orchestrator_error"] = str(e)
    try:
        import providers  # noqa: F401
        imports["providers"] = True
    except Exception as e:
        imports["providers"] = False
        imports["providers_error"] = str(e)

    payload["imports"] = imports
    payload["missing_required"] = missing_required()
    payload["missing_recommended"] = missing_recommended()
    return jsonify(payload), 200

@app.get("/ping")
def ping():
    return "pong", 200

@app.get("/docs")
def docs():
    return jsonify({"supported_formats": SUPPORTED_FORMATS})

@app.post("/webhook")
def webhook():
    data, raw_len = _read_update_json()
    req_id = request.environ.get("TKC_REQ_ID")

    log_info("Webhook received", req_id=req_id, method=request.method, path=request.path, size=raw_len)

    if not data:
        log_warn("No JSON data received from Telegram", req_id=req_id)
        return jsonify({"status": "ok"}), 200

    # Log แบบปลอดภัย: โชว์แค่ update_id / chat_id mask
    try:
        upd_id = data.get("update_id")
        chat_id = None
        if "message" in data:
            chat_id = (data["message"].get("chat") or {}).get("id")
        elif "edited_message" in data:
            chat_id = (data["edited_message"].get("chat") or {}).get("id")
        elif "channel_post" in data:
            chat_id = (data["channel_post"].get("chat") or {}).get("id")
        elif "callback_query" in data:
            cq = data["callback_query"]
            if cq.get("message") and cq["message"].get("chat"):
                chat_id = cq["message"]["chat"].get("id")
        log_info("Update meta", req_id=req_id, update_id=upd_id, chat=_mask(chat_id))
    except Exception:
        pass

    # ส่งต่อให้ handler หลัก (ภายในมี dedupe อีกชั้น)
    try:
        handle_message(data)
    except Exception as e:
        log_err("Handler error", req_id=req_id, err=str(e), tb=traceback.format_exc())

    # ตอบ Telegram ทันทีเพื่อกัน retry
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    log_info(f"Starting TKC Telegram Bot on port {port}", debug=debug_mode, git_sha=GIT_SHA or None)
    try:
        app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=debug_mode)
    except KeyboardInterrupt:
        log_info("Received KeyboardInterrupt. Shutting down TKC Telegram Bot.")
