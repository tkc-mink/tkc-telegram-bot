# config.py
import os

# ==========================
# Environment Configurations
# ==========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise EnvironmentError("TELEGRAM_TOKEN หรือ OPENAI_API_KEY ไม่ถูกตั้งค่าใน environment variable!")

# ==========================
# File Paths & Constants
# ==========================

USAGE_FILE           = "usage.json"
IMAGE_USAGE_FILE     = "image_usage.json"
CONTEXT_FILE         = "context_history.json"
LOCATION_FILE        = "location_logs.json"

# ==========================
# Limits & Access Control
# ==========================

MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY    = 15
EXEMPT_USER_IDS      = ["6849909227"]

# ==========================
# Other (for easy extend)
# ==========================

# สามารถเพิ่มค่า config อื่นๆ ที่ใช้ร่วมกันที่นี่ได้
