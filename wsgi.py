# run.py
# -*- coding: utf-8 -*-
"""
ไฟล์สำหรับรัน Flask app
รองรับทั้งโหมด development และ production (dev server)
"""
from __future__ import annotations
import os
import sys

# (ออปชัน) โหลด .env ถ้ามีและติดตั้ง python-dotenv ไว้
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# นำเข้าแอปหลัก
try:
    from main import app  # ต้องมีตัวแปร Flask ชื่อ app
except Exception as e:
    print(f"[run] Failed to import app from main: {e}", file=sys.stderr)
    raise

def _truthy(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "on"}

if __name__ == "__main__":
    # Read host/port/debug อย่างยืดหยุ่น
    host = os.getenv("HOST") or os.getenv("BIND") or os.getenv("FLASK_RUN_HOST") or "0.0.0.0"
    try:
        port = int(os.getenv("PORT") or os.getenv("FLASK_RUN_PORT") or 5000)
    except ValueError:
        port = 5000

    debug = _truthy(os.getenv("DEBUG") or os.getenv("FLASK_DEBUG"), False)
    use_reloader = _truthy(os.getenv("FLASK_USE_RELOADER"), debug)
    threaded = _truthy(os.getenv("FLASK_THREADED"), True)

    # HTTPS ถ้าตั้ง cert/key ไว้
    certfile = os.getenv("SSL_CERTFILE")
    keyfile = os.getenv("SSL_KEYFILE")
    ssl_context = (certfile, keyfile) if (certfile and keyfile) else None

    if not debug:
        print("[run] WARNING: Running Flask dev server in production mode. "
              "แนะนำให้ใช้ gunicorn/uwsgi/waitress สำหรับโปรดักชัน.", file=sys.stderr)

    print(f"[run] Starting Flask on {host}:{port} (debug={debug}, reloader={use_reloader}, threaded={threaded})")
    if ssl_context:
        print("[run] HTTPS enabled via SSL_CERTFILE/SSL_KEYFILE")

    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=use_reloader,
        threaded=threaded,
        ssl_context=ssl_context,
    )
