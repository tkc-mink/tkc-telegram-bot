# settings.py

import os

# === Global Settings ===
DEBUG_MODE = bool(os.environ.get("FLASK_DEBUG", "0") == "1")

# === Daily Backup Schedule (Asia/Bangkok, 00:09) ===
BACKUP_TIME_HOUR = 0
BACKUP_TIME_MINUTE = 9

# === Document Types Supported for Upload/Preview ===
SUPPORTED_FORMATS = [
    ".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".jpg", ".png"
]
