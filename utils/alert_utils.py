# utils/alert_utils.py
import os
import json
from utils.message_utils import send_message

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # ใส่ chat_id คุณชลิตที่นี่ หรือ fix id ตรงๆ

def check_and_alert():
    """
    ตัวอย่าง: แจ้งเตือนเมื่อคำถามซ้ำผิดปกติ หรือใช้งานเยอะผิดปกติ
    (ปรับ logic ตามต้องการ)
    """
    history_dir = "chat_logs"
    logs = []
    if os.path.exists(history_dir):
        for fname in os.listdir(history_dir):
            fpath = os.path.join(history_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    logs.extend(json.load(f))
            except Exception:
                continue
    # ตัวอย่าง: ถ้าวันนี้มีการถามซ้ำมากกว่า 3 ครั้งในประเด็นเดียว
    counts = {}
    for l in logs[-100:]:  # ตรวจสอบ log 100 รายการล่าสุด
        q = l.get("q", "")
        counts[q] = counts.get(q, 0) + 1
        if counts[q] == 4:
            send_message(ADMIN_CHAT_ID, f"⚠️ พบการถามซ้ำบ่อย: '{q}' เกิน 3 ครั้งล่าสุด")
