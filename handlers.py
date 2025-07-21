import os
import json
from datetime import datetime
import requests
from openai import OpenAI
from search_utils import robust_image_search
from review_utils import set_review, need_review_today, has_reviewed_today
from history_utils import log_message, get_user_history
from weather_utils import get_weather_forecast
from gold_utils import get_gold_price
from news_utils import get_news

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE = "usage.json"
IMAGE_USAGE_FILE = "image_usage.json"
CONTEXT_FILE = "context_history.json"
LOCATION_FILE = "location_logs.json"

MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY = 15
EXEMPT_USER_IDS = ["6849909227"]  # Telegram ID ที่ไม่จำกัดการใช้งาน

# โหลดข้อมูล JSON จากไฟล์ด้วยความปลอดภัย
def load_json_safe(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# บันทึกข้อมูล JSON ลงไฟล์อย่างปลอดภัย
def save_json_safe(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[save_json_safe] Error saving {filename}: {e}")

# ตรวจสอบและเพิ่มการใช้งานรายวันของ user
def check_and_increase_usage(user_id, filename, max_count):
    today = datetime.now().strftime("%Y-%m-%d")
    usage = load_json_safe(filename)
    usage.setdefault(today, {})
    usage[today].setdefault(user_id, 0)
    if usage[today][user_id] >= max_count:
        return False
    usage[today][user_id] += 1
    save_json_safe(usage, filename)
    return True

def load_context():
    return load_json_safe(CONTEXT_FILE)

def save_context(data):
    save_json_safe(data, CONTEXT_FILE)

def update_context(user_id, user_text):
    context = load_context()
    context.setdefault(user_id, [])
    context[user_id].append(user_text)
    # เก็บแค่ 5 ข้อความล่าสุด
    context[user_id] = context[user_id][-5:]
    save_context(context)

def get_context(user_id):
    context = load_context()
    return context.get(user_id, [])

def is_waiting_review(user_id):
    context = get_context(user_id)
    return context and context[-1] == "__wait_review__"

def load_location():
    return load_json_safe(LOCATION_FILE)

def save_location(data):
    save_json_safe(data, LOCATION_FILE)

def update_location(user_id, lat, lon, province=None, country=None):
    loc = load_location()
    loc[user_id] = {
        "lat": lat,
        "lon": lon,
        "province": province,
        "country": country,
        "ts": datetime.now().isoformat()
    }
    save_location(loc)

def get_user_location(user_id):
    loc = load_location()
    return loc.get(user_id, {})

def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5
        )
    except Exception as e:
        print(f"[send_message] Error: {e}")

def send_photo(chat_id, photo_url, caption=None):
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json=data,
            timeout=5
        )
    except Exception as e:
        print(f"[send_photo] Error: {e}")

def generate_image_search_keyword(user_text, context_history=None):
    system_prompt = (
        "คุณคือ AI ที่เก่งเรื่องค้นหารูปจากอินเทอร์เน็ต ให้คิด 'คำค้น' (search keyword) ที่เหมาะสมที่สุดจากโจทย์ของผู้ใช้ "
        "ถ้าโจทย์ไม่ครบให้เติมหรือเดาเองโดยสมเหตุสมผล ภาษาอังกฤษจะดีสุด "
        "ถ้าข้อความใหม่คลุมเครือ ให้เชื่อมโยงกับคำถามก่อนหน้า (context) ของ user "
        "ตัวอย่าง: ถ้าผู้ใช้เพิ่งถาม 'ขอรูปยาง...' แล้วต่อด้วย 'ดอกอื่นมีอีกไหม' ให้เข้าใจว่า 'ดอก' หมายถึง 'ดอกยาง' ไม่ใช่ดอกไม้"
    )
    messages = [{"role": "system", "content": system_prompt}]
    if context_history:
        for prev in context_history[-2:]:
            messages.append({"role": "user", "content": prev})
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=50,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[generate_image_search_keyword] GPT Error: {e}")
        return user_text  # fallback ใช้ข้อความเดิม

def handle_image_search(chat_id, user_id, user_text, context_history):
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY):
            send_message(chat_id, f"ขออภัย คุณขอรูปครบ {MAX_IMAGE_PER_DAY} รูปแล้วในวันนี้")
            return

    keyword = generate_image_search_keyword(user_text, context_history)
    images = robust_image_search(keyword)
    if images:
        for url in images[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์สำหรับคำค้น: {keyword}")
    else:
        send_message(chat_id, f"ขออภัย ไม่พบรูปภาพสำหรับ '{keyword}' จากทุกแหล่งครับ ลองเปลี่ยนรายละเอียดหรือระบุข้อมูลเพิ่มเติม เช่น ยี่ห้อ รุ่น สี ปี ฯลฯ")

def handle_message(data):
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        print("[handle_message] Missing chat_id")
        return

    user_text = message.get("caption", "") or message.get("text", "")
    user_id = str(chat_id)

    # รับ location (ถ้ามี)
    if "location" in message:
        loc = message["location"]
        lat = loc.get("latitude")
        lon = loc.get("longitude")
        if lat is not None and lon is not None:
            update_location(user_id, lat, lon)
            send_message(chat_id, "บันทึกพิกัดสำเร็จ! จะใช้ในการตอบอากาศ/ข้อมูลเฉพาะพื้นที่")
        else:
            send_message(chat_id, "ได้รับข้อมูลตำแหน่งไม่ครบถ้วน กรุณาลองใหม่อีกครั้ง")
        return

    update_context(user_id, user_text)
    context_history = get_context(user_id)

    # ==== /my_history (ประวัติย้อนหลัง) ====
    if user_text.strip() == "/my_history":
        history = get_user_history(user_id, limit=10)
        if not history:
            send_message(chat_id, "ยังไม่มีประวัติการถาม-ตอบย้อนหลังของคุณ")
        else:
            history_str = "\n\n".join(
                [f"[{item['date']}] ❓{item['q']}\n➡️ {item['a']}" for item in history]
            )
            send_message(chat_id, f"ประวัติ 10 ข้อความล่าสุดของคุณ:\n\n{history_str}")
        return

    # ==== ระบบรีวิว ====
    if need_review_today(user_id) and not is_waiting_review(user_id):
        send_message(chat_id, "ขอรีวิวความพึงพอใจที่ได้ใช้บอทเมื่อวานนี้ (1=ไม่พอใจ, 5=พอใจมาก) กรุณาพิมพ์เลข 1-5")
        update_context(user_id, "__wait_review__")
        return

    if is_waiting_review(user_id) and user_text.strip() in ["1", "2", "3", "4", "5"]:
        set_review(user_id, int(user_text.strip()))
        send_message(chat_id, "ขอบคุณสำหรับรีวิวครับ!")
        update_context(user_id, "__reviewed__")
        if user_text.strip() in ["1", "2"]:
            send_message(chat_id, "รบกวนช่วยบอกเหตุผลหรือข้อติชมที่ทำให้ยังไม่พอใจ เพื่อให้ทีมงานปรับปรุงให้ดีขึ้นได้ไหมครับ")
        return

    # ==== จำกัดรอบ ====
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, USAGE_FILE, MAX_QUESTION_PER_DAY):
            send_message(chat_id, f"ขออภัย คุณใช้งานครบ {MAX_QUESTION_PER_DAY} ครั้งแล้วในวันนี้")
            return

    txt = user_text.lower()
    user_loc = get_user_location(user_id)

    # ----- พยากรณ์อากาศ -----
    if "อากาศ" in txt or "weather" in txt:
        if user_loc.get("lat") and user_loc.get("lon"):
            reply = get_weather_forecast(user_text, user_loc["lat"], user_loc["lon"])
        else:
            reply = get_weather_forecast(user_text)
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
        return

    # ----- ราคาทอง -----
    if "ราคาทอง" in txt or "gold" in txt:
        reply = get_gold_price()
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
        return

    # ----- ข่าว -----
    if "ข่าว" in txt or "news" in txt:
        reply = get_news(user_text)
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
        return

    # ----- ขอรูป -----
    if any(k in txt for k in ["ขอรูป", "มีภาพ", "image", "picture", "photo", "รูป", "ภาพ"]):
        handle_image_search(chat_id, user_id, user_text, context_history)
        log_message(user_id, user_text, "ภาพที่ส่งกลับ (ดูในแชท)")
        return

    # ----- Default: ส่งเข้า GPT-4o -----
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_text}],
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[handle_message] GPT API error: {e}")
        reply = "ขออภัยครับ เกิดปัญหาในการประมวลผลข้อความของคุณ กรุณาลองใหม่อีกครั้ง"

    log_message(user_id, user_text, reply)
    send_message(chat_id, reply)
