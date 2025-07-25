# utils/report_utils.py
import os
import json
from datetime import datetime, timedelta

def _load_history():
    """โหลด log คำถามย้อนหลัง (ใช้ไฟล์/โฟลเดอร์ history จริง)"""
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
    return logs

def get_daily_report():
    logs = _load_history()
    today = datetime.now().date()
    today_logs = [l for l in logs if l.get("date", "")[:10] == str(today)]
    n_users = len(set(l.get("user_id") for l in today_logs))
    n_q = len(today_logs)
    top3 = {}
    for l in today_logs:
        key = l.get("q", "").split()[0]
        if key:
            top3[key] = top3.get(key, 0) + 1
    tops = sorted(top3.items(), key=lambda x: -x[1])[:3]
    tops_text = "\n".join([f"• {k}: {v} ครั้ง" for k, v in tops]) if tops else "-"
    return (
        f"📊 <b>สรุปการใช้งานวันนี้</b>\n"
        f"👥 ผู้ใช้ที่ถาม: {n_users} คน\n"
        f"❓ คำถามทั้งหมด: {n_q} ข้อ\n"
        f"⭐️ คำถามยอดนิยม:\n{tops_text}"
    )

def get_weekly_report():
    logs = _load_history()
    week_ago = datetime.now() - timedelta(days=7)
    week_logs = [l for l in logs if l.get("date", "")[:10] >= week_ago.strftime("%Y-%m-%d")]
    n_users = len(set(l.get("user_id") for l in week_logs))
    n_q = len(week_logs)
    top3 = {}
    for l in week_logs:
        key = l.get("q", "").split()[0]
        if key:
            top3[key] = top3.get(key, 0) + 1
    tops = sorted(top3.items(), key=lambda x: -x[1])[:3]
    tops_text = "\n".join([f"• {k}: {v} ครั้ง" for k, v in tops]) if tops else "-"
    return (
        f"📈 <b>สรุปการใช้งาน 7 วันล่าสุด</b>\n"
        f"👥 ผู้ใช้ที่ถาม: {n_users} คน\n"
        f"❓ คำถามทั้งหมด: {n_q} ข้อ\n"
        f"⭐️ คำถามยอดนิยม:\n{tops_text}"
    )
