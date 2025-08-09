# settings.py
# -*- coding: utf-8 -*-
"""
Global settings สำหรับ TKC Telegram Bot
"""

import os

# =====================
# Global Flags
# =====================
DEBUG_MODE = bool(os.environ.get("FLASK_DEBUG", "0") == "1")

# =====================
# Backup Scheduler Config
# =====================
# Daily Backup Schedule (Asia/Bangkok)
# ตั้งให้รันเวลา 00:09 น.
BACKUP_TIME_HOUR = int(os.environ.get("BACKUP_TIME_HOUR", 0))
BACKUP_TIME_MINUTE = int(os.environ.get("BACKUP_TIME_MINUTE", 9))

# =====================
# Document Upload/Preview Support
# =====================
SUPPORTED_FORMATS = [
    ".pdf",  # Portable Document Format
    ".docx", # Microsoft Word Document
    ".txt",  # Plain Text
    ".xlsx", # Microsoft Excel
    ".pptx", # Microsoft PowerPoint
    ".jpg",  # JPEG Image
    ".png",  # PNG Image
]
