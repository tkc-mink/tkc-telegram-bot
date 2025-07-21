import os
import json
from datetime import datetime
import requests
from openai import OpenAI
from search_utils import robust_image_search
from review_utils import set_review, need_review_today, has_reviewed_today
from history_utils import log_message, get_user_history

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE = "usage.json"
IMAGE_USAGE_FILE = "image_usage.json"
CONTEXT_FILE = "context_history.json"
MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY = 15

EXEMPT_USER_IDS = ["6849909227"]

def load_usage(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_usage(data, file):
    with open(file, "w") as f:
        json.dump(data, f)

def check_and_increase_usage(user_id, file, max_count):
    today = datetime.now().strftime("%Y-%m-%d")
    usage = load_usage(file)
    usage.setdefault(today, {})
    usage[today].setdefault(user_id, 0)
    if usage[today][user_id] >= max_count:
        return False
    usage[today][user_id] += 1
    save_usage(usage, file)
    return True

def load_context():
    try:
        with open(CONTEXT_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_context(data):
    with open(CONTEXT_FILE, "w") as f:
        json.dump(data, f)

def update_context(user_id, user_text):
    context = load_context()
    context.setdefault(user_id, [])
    context[user_id].append(user_text)
    context[user_id] = context[user_id][-5:]
    save_context(context)

def get_context(user_id):
    context = load_context()
    return context.get(user_id, [])

def is_waiting_review(user_id):
    context = get_context(user_id)
    return context and context[-1] == "__wait_review__"

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def send_photo(chat_id, photo_url, caption=None):
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
        json=data
    )

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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=50,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

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
    chat_id = message["chat"]["id"]
    user_text = message.get("caption", "") or message.get("text", "")
    user_id = str(chat_id)

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

    # ==== ขอรูป ====
    if any(k in user_text.lower() for k in ["ขอรูป", "มีภาพ", "image", "picture", "photo", "รูป", "ภาพ"]):
        handle_image_search(chat_id, user_id, user_text, context_history)
        log_message(user_id, user_text, "ภาพที่ส่งกลับ (ดูในแชท)")
    else:
        # ==== ส่งคำถามเข้า GPT4o + log history ====
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_text}],
        )
        reply = response.choices[0].message.content.strip()
        log_message(user_id, user_text, reply)
        send_message(chat_id, reply)
