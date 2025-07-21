# handlers.py

import os
import json
from datetime import datetime
import requests
from openai import OpenAI

from search_utils    import robust_image_search
from review_utils    import set_review, need_review_today, has_reviewed_today
from history_utils   import log_message, get_user_history
from weather_utils   import get_weather_forecast
from gold_utils      import get_gold_price
from news_utils      import get_news

# ─── Configuration ────────────────────────────────────────

TELEGRAM_TOKEN       = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")
client               = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE           = "usage.json"
IMAGE_USAGE_FILE     = "image_usage.json"
CONTEXT_FILE         = "context_history.json"
LOCATION_FILE        = "location_logs.json"

MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY    = 15
EXEMPT_USER_IDS      = ["6849909227"]  # Telegram IDs ไม่ถูกจำกัด

# ─── JSON I/O Helpers ─────────────────────────────────────

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
        print(f"[save_json_safe] {path}: {e}")

# ─── Usage Counting ───────────────────────────────────────

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

# ─── Context Memory ──────────────────────────────────────

def load_context():
    return load_json_safe(CONTEXT_FILE)

def save_context(ctx):
    save_json_safe(ctx, CONTEXT_FILE)

def update_context(user_id, text):
    ctx = load_context()
    ctx.setdefault(user_id, []).append(text)
    ctx[user_id] = ctx[user_id][-5:]
    save_context(ctx)

def get_context(user_id):
    return load_context().get(user_id, [])

# ─── Location Logging ────────────────────────────────────

def load_location():
    return load_json_safe(LOCATION_FILE)

def save_location(loc):
    save_json_safe(loc, LOCATION_FILE)

def update_location(user_id, lat, lon):
    loc = load_location()
    loc[user_id] = {
        "lat": lat,
        "lon": lon,
        "ts": datetime.now().isoformat()
    }
    save_location(loc)

def get_user_location(user_id):
    return load_location().get(user_id)

# ─── Telegram Send Helpers ───────────────────────────────

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
            [
                {"text": "📍 แชร์ตำแหน่งของคุณ", "request_location": True}
            ]
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

# ─── Image Search ────────────────────────────────────────

def generate_image_search_keyword(user_text, context_history):
    system_prompt = (
        "คุณคือ AI ช่วยคิดคำค้นรูปภาพจากโจทย์ผู้ใช้ หากโจทย์ไม่ครบ ให้อยูตรวมเอง "
        "และ output เป็น keyword ภาษาอังกฤษที่ได้ผลดีที่สุด"
    )
    messages = [{"role":"system","content":system_prompt}]
    for prev in context_history[-2:]:
        messages.append({"role":"user","content":prev})
    messages.append({"role":"user","content":user_text})
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=50,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[generate_image_search_keyword] {e}")
        return user_text

def handle_image_search(chat_id, user_id, text, ctx):
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY):
            send_message(chat_id, f"❌ ครบ {MAX_IMAGE_PER_DAY} รูปวันนี้แล้ว")
            return
    kw = generate_image_search_keyword(text, ctx)
    imgs = robust_image_search(kw)
    if imgs:
        for url in imgs[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์: {kw}")
    else:
        send_message(chat_id, f"ไม่พบภาพสำหรับ '{kw}'")

# ─── Main Handler ────────────────────────────────────────

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

    # 2) Update Context
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
    if need_review_today(user_id) and not has_reviewed_today(user_id):
        send_message(chat_id, "❓ กรุณารีวิววันนี้ (1-5):")
        return

    # 5) จำกัดรอบถาม
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, USAGE_FILE, MAX_QUESTION_PER_DAY):
            send_message(chat_id, f"❌ ครบ {MAX_QUESTION_PER_DAY} คำถามแล้ววันนี้")
            return

    txt = user_text.lower()
    loc = get_user_location(user_id)

    # 6) พยากรณ์อากาศ
    if "อากาศ" in txt or "weather" in txt:
        if loc and loc.get("lat") and loc.get("lon"):
            reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
        else:
            ask_for_location(chat_id)
        log_message(user_id, user_text, reply if 'reply' in locals() else "ขอ Location")
        return

    # 7) ราคาทอง
    if "ราคาทอง" in txt or "gold" in txt:
        reply = get_gold_price()
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
        return

    # 8) ข่าว
    if "ข่าว" in txt or "news" in txt:
        reply = get_news(user_text)
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
        return

    # 9) รูปภาพ
    if any(k in txt for k in ["ขอรูป", "รูป", "image", "photo"]):
        handle_image_search(chat_id, user_id, user_text, ctx)
        log_message(user_id, user_text, "ส่งรูปภาพ (ดูในแชท)")
        return

    # 10) Fallback → GPT-4o
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"user","content":user_text}]
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT] {e}")
        reply = "❌ เกิดปัญหาในการประมวลผล ลองใหม่อีกครั้ง"

    log_message(user_id, user_text, reply)
    send_message(chat_id, reply)
