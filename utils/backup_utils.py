import json
from datetime import datetime

def get_backup_status():
    try:
        with open("data/backup_log.json", "r", encoding="utf-8") as f:
            log = json.load(f)
        return {
            "last_backup": log.get("last_backup"),
            "files": log.get("files"),
            "result": log.get("result"),
        }
    except Exception:
        return None
