from datetime import datetime, timedelta

def now_str(fmt="%Y-%m-%d %H:%M:%S"):
    """คืนค่าเวลาปัจจุบันในรูปแบบ string ที่กำหนด"""
    return datetime.now().strftime(fmt)

def today_str(fmt="%Y-%m-%d"):
    """คืนค่าวันนี้"""
    return datetime.now().strftime(fmt)

def yesterday_str(fmt="%Y-%m-%d"):
    """คืนค่าวันเมื่อวาน"""
    return (datetime.now() - timedelta(days=1)).strftime(fmt)

def is_today(date_str, fmt="%Y-%m-%d"):
    """ตรวจสอบว่า date_str เป็นวันนี้ไหม"""
    try:
        return date_str == today_str(fmt)
    except Exception:
        return False

def days_between(date1, date2, fmt="%Y-%m-%d"):
    """คืนค่าจำนวนวันระหว่างวันที่สองวัน (date1, date2)"""
    try:
        d1 = datetime.strptime(date1, fmt)
        d2 = datetime.strptime(date2, fmt)
        return abs((d2 - d1).days)
    except Exception as e:
        print(f"[date_utils] error: {e}")
        return None
