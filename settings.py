# settings.py

import os

DEBUG_MODE = bool(os.environ.get("FLASK_DEBUG", "0") == "1")
BACKUP_TIME_HOUR = 0
BACKUP_TIME_MINUTE = 9

SUPPORTED_FORMATS = [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".jpg", ".png"]
