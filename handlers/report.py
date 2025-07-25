# handlers/report.py
from utils.report_utils import get_daily_report, get_weekly_report
from utils.message_utils import send_message

def handle_report(chat_id, user_text):
    """/report หรือ /summary"""
    text = user_text.strip().lower()
    if "week" in text or "สัปดาห์" in text:
        msg = get_weekly_report()
    else:
        msg = get_daily_report()
    send_message(chat_id, msg)
