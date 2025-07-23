# config.py

import os
from openai import OpenAI

TELEGRAM_TOKEN      = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
client              = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE           = "usage.json"
IMAGE_USAGE_FILE     = "image_usage.json"
CONTEXT_FILE         = "context_history.json"
LOCATION_FILE        = "location_logs.json"
MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY    = 15
EXEMPT_USER_IDS      = ["6849909227"]
