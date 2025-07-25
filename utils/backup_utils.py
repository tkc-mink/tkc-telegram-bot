# utils/backup_utils.py

import json
from datetime import datetime

BACKUP_LOG_PATH = "data/backup_log.json"

def get_backup_status():
    """
    อ่านสถานะล่าสุดของการ backup จากไฟล์ log
    """
    try:
        with open(BACKUP_LOG_PATH, "r", encoding="utf-8") as f:
            log = json.load(f)
        # ตรวจสอบ timestamp และข้อมูลเบื้องต้น
        last_backup = log.get("last_backup")
        files = log.get("files", [])
        status = log.get("status", "unknown")
        details = log.get("details", "")
        # ตรวจสอบอายุ backup (ถ้าจำเป็น)
        return {
            "last_backup": last_backup,
            "files": files,
            "status": status,
            "details": details
        }
    except Exception as e:
        return None
