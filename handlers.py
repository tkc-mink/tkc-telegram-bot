# handlers.py

import os
import json
from datetime import datetime
import requests
from openai import OpenAI

from search_utils      import robust_image_search
from review_utils      import set_review, need_review_today
from history_utils     import log_message, get_user_history
from weather_utils     import get_weather_forecast
from gold_utils        import get_gold_price
from news_utils        import get_news
from serp_utils        import get_stock_info, get_oil_price, get_lottery_result, get_crypto_price
from function_calling  import process_with_function_calling

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client         = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE           = "usage.json"
IMAGE_USAGE_FILE     = "image_usage.json"
CONTEXT_FILE         = "context_history.json"
LOCATION_FILE        = "location_logs.json"
MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY    = 15
EXEMPT_USER_IDS      = ["6849909227"]  # Telegram IDs ไม่ถูกจำกัด

# JSON helpers
def load_json_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}
def save_json_safe(data, path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_json_safe:{path}] {e}")

def check_and_increase_usage(user_id, filepath, limit):
    today = datetime.now().strftime("%Y-%m-%d")
    usage = load_json_safe(filepath)
    usage.setdefault(today, {})
    usage[today].setdefault(user_id, 0)
    if usage[today][user_id] >= limit:
        return False
    usage[today][user_id] += 1
    save_json_safe(usage, filepath)
    return True

def load_context():
    return load_json_safe(CONTEXT_FILE)
def save_context(ctx):
    save_json_safe(ctx, CONTEXT_FILE)
def update_context(user_id, text):
    ctx = load_context()
    ctx.setdefault(user_id, []).append(text)
    ctx[user_id] = ctx[user_id][-6:]
    save_context(ctx)
def get_context(user_id):
    return load_context().get(user_id, [])
def is_waiting_review(user_id):
    ctx = get_context(user_id)
    return ctx and ctx[-1] == "__wait_review__"

def load_location():
    return load_json_safe(LOCATION_FILE)
def save_location(loc):
    save_json_safe(loc, LOCATION_FILE)
def update_location(user_id, lat, lon):
    loc = load_location()
    loc[user_id] = {"lat": lat, "lon": lon, "ts": datetime.now().isoformat()}
    save_location(loc)
def get_user_location(user_id):
    return load_location().get(user_id)

def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5
        )
    except Exception as e:
        print(f"[send_message] {e}")

def send_photo(chat_id, photo_url, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"[send_photo] {e}")

def ask_for_location(chat_id, text="📍 กรุณาแชร์ตำแหน่งของคุณ"):
    keyboard = {
        "keyboard": [
            [ {"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True} ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    }
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"[ask_for_location] {e}")

def handle_image_search(chat_id, user_id, text, ctx):
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY):
            send_message(chat_id, f"❌ ครบ {MAX_IMAGE_PER_DAY} รูปวันนี้แล้ว")
            return
    kw = text
    imgs = robust_image_search(kw)
    if imgs:
        for url in imgs[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์: {kw}")
    else:
        send_message(chat_id, f"ไม่พบภาพสำหรับ '{kw}'")

def handle_message(data):
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return
    user_text = msg.get("caption", "") or msg.get("text", "")
    user_id   = str(chat_id)

    # 1) รับ Location
    if "location" in msg:
        lat = msg["location"].get("latitude")
        lon = msg["location"].get("longitude")
        if lat is not None and lon is not None:
            update_location(user_id, lat, lon)
            send_message(chat_id, "✅ บันทึกตำแหน่งแล้ว! ลองถามอากาศอีกครั้งได้เลย")
        else:
            send_message(chat_id, "❌ ตำแหน่งไม่ถูกต้อง กรุณาส่งใหม่")
        return

    if user_text.strip() == "📍 แชร์ตำแหน่งของคุณ":
        ask_for_location(chat_id)
        return

    update_context(user_id, user_text)
    ctx = get_context(user_id)

    # 3) /my_history
    if user_text.strip() == "/my_history":
        history = get_user_history(user_id, limit=10)
        if not history:
            send_message(chat_id, "ยังไม่มีประวัติการถาม-ตอบของคุณ")
        else:
            out = "\n\n".join(f"[{it['date']}] ❓{it['q']}\n➡️ {it['a']}" for it in history)
            send_message(chat_id, f"ประวัติ 10 ล่าสุด:\n\n{out}")
        return

    # 4) รีวิว
    if need_review_today(user_id) and not is_waiting_review(user_id):
        send_message(chat_id, "❓ กรุณารีวิววันนี้ (1-5):")
        update_context(user_id, "__wait_review__")
        return
    if is_waiting_review(user_id) and user_text.strip() in ["1","2","3","4","5"]:
        set_review(user_id, int(user_text.strip()))
        send_message(chat_id, "✅ ขอบคุณสำหรับรีวิวครับ!")
        return

    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, USAGE_FILE, MAX_QUESTION_PER_DAY):
            send_message(chat_id, f"❌ ครบ {MAX_QUESTION_PER_DAY} คำถามแล้ววันนี้")
            return

    txt = user_text.lower()
    loc = get_user_location(user_id)

    if "อากาศ" in txt or "weather" in txt:
        if loc and loc.get("lat") and loc.get("lon"):
            reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
            send_message(chat_id, reply)
        else:
            ask_for_location(chat_id)
        return

    if any(k in txt for k in ["ขอรูป","รูป","image","photo"]):
        handle_image_search(chat_id, user_id, user_text, ctx)
        log_message(user_id, user_text, "ส่งรูปภาพ (ดูในแชท)")
        return

    # == Fallback → GPT-4o + Function Calling (Context-aware) ==
    try:
        reply = process_with_function_calling(user_text, ctx=ctx)
    except Exception as e:
        print(f"[GPT function_calling] {e}")
        reply = "❌ ระบบขัดข้อง ลองใหม่อีกครั้ง"

    log_message(user_id, user_text, reply)
    send_message(chat_id, reply)
