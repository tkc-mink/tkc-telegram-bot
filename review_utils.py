import json
from datetime import datetime, timedelta

REVIEW_FILE = "review.json"
USAGE_FILE = "usage.json"

def load_review():
    try:
        with open(REVIEW_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_review(data):
    with open(REVIEW_FILE, "w") as f:
        json.dump(data, f)

def set_review(user_id, rating):
    today = datetime.now().strftime("%Y-%m-%d")
    data = load_review()
    data.setdefault(today, {})
    data[today][user_id] = rating
    save_review(data)

def get_review(date, user_id):
    data = load_review()
    return data.get(date, {}).get(user_id, None)

def has_reviewed_today(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    return get_review(today, user_id) is not None

def need_review_today(user_id):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        with open(USAGE_FILE, "r") as f:
            usage = json.load(f)
        if user_id in usage.get(yesterday, {}):
            return not has_reviewed_today(user_id)
    except:
        pass
    return False
