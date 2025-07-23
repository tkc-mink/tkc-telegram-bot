from datetime import datetime
from utils.json_utils import load_json_safe, save_json_safe

USAGE_FILE = "usage.json"

def check_and_increase_usage(user_id, filepath=USAGE_FILE, limit=30):
    today = datetime.now().strftime("%Y-%m-%d")
    usage = load_json_safe(filepath)
    usage.setdefault(today, {})
    usage[today].setdefault(user_id, 0)
    if usage[today][user_id] >= limit:
        return False
    usage[today][user_id] += 1
    save_json_safe(usage, filepath)
    return True
