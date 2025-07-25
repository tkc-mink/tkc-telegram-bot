# utils/faq_utils.py
import os
import json

FAQ_FILE = "data/faq_list.json"

def get_faq_list():
    if os.path.exists(FAQ_FILE):
        with open(FAQ_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def add_faq(q):
    faqs = get_faq_list()
    if q not in faqs:
        faqs.append(q)
        os.makedirs(os.path.dirname(FAQ_FILE), exist_ok=True)
        with open(FAQ_FILE, "w", encoding="utf-8") as f:
            json.dump(faqs, f, ensure_ascii=False, indent=2)
