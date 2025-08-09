# run.py
# -*- coding: utf-8 -*-
"""
ไฟล์สำหรับรัน Flask app
รองรับทั้งโหมด development และ production
"""

from main import app
import os

if __name__ == "__main__":
    # อ่าน host/port จาก ENV ถ้าไม่มีให้ใช้ค่า default
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)
