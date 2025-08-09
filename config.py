# config.py
# -*- coding: utf-8 -*-
"""
Environment variables และค่าคงที่ที่ใช้ทั้งโปรเจกต์
"""

import os

# ==========================
# Environment Configurations
# ==========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise EnvironmentError(
        "❌ TELEGRAM_TOKEN หรือ OPENAI_API_KEY ไม่ถูกตั้งค่าใน environment variable!"
    )

# ==========================
# File Paths & Constants
# ==========================
USAGE_FILE        = os.getenv("USAGE_FILE", "usage.json")
IMAGE_USAGE_FILE  = os.getenv("IMAGE_USAGE_FILE", "image_usage.json")
CONTEXT_FILE      = os.getenv("CONTEXT_FILE", "context_history.json")
LOCATION_FILE     = os.getenv("LOCATION_FILE", "location_logs.json")

# ==========================
# Limits & Access Control
# ==========================
MAX_QUESTION_PER_DAY = int(os.getenv("MAX_QUESTION_PER_DAY", 30))
MAX_IMAGE_PER_DAY    = int(os.getenv("MAX_IMAGE_PER_DAY", 15))

# รายชื่อ user id ที่ไม่จำกัดการใช้งาน
EXEMPT_USER_IDS = os.getenv("EXEMPT_USER_IDS", "6849909227").split(",")

# ==========================
# Other Settings
# ==========================
# SUPPORTED_FORMATS สามารถดึงจาก settings.py ได้ เพื่อให้เป็นแหล่งข้อมูลเดียว
