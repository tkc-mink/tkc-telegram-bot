# handlers.py

import os
import json
from datetime import datetime
import requests
from openai import OpenAI
from search_utils import robust_image_search  # ต้องมี robust_image_search ใน search_utils.py

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

USAGE_FILE = "usage.json"
IMAGE_USAGE_FILE = "image_usage.json"
MAX_QUESTION_PER_DAY = 30
MAX_IMAGE_PER_DAY = 15

# เพิ่ม user id admin/owner ที่ไม่ต้องจำกัดรอบ
EXEMPT_USER_IDS = ["123456789"]  # เช่น chat_id ของคุณชลิต/เจ้าของกิจการ (string)

# === ฟังก์ชันนับจำนวนรอบถาม ===
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

# === ฟังก์ชันตอบกลับ Telegram ===
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

# === AI สร้าง keyword สำหรับค้นรูป ===
def generate_image_search_keyword(user_text):
    system_prompt = (
        "คุณคือ AI ที่เก่งเรื่องค้นหารูปจากอินเทอร์เน็ต ให้คิด 'คำค้น' (search keyword) ที่เหมาะสมที่สุดจากโจทย์ของผู้ใช้ "
        "ถ้าโจทย์ไม่ครบให้เติมหรือเดาเองโดยสมเหตุสมผล ภาษาอังกฤษจะดีสุด เช่น 'bridgestone 265/65R17 all terrain tire', 'cat cartoon cute', 'toyota commuter 2023 white van'"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        max_tokens=50,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()

# === handle image search + นับ quota ภาพแยก ===
def handle_image_search(chat_id, user_id, user_text):
    # admin/owner ไม่ต้องนับ quota ขอภาพ
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, IMAGE_USAGE_FILE, MAX_IMAGE_PER_DAY):
            send_message(chat_id, f"ขออภัย คุณขอรูปครบ {MAX_IMAGE_PER_DAY} รูปแล้วในวันนี้")
            return

    keyword = generate_image_search_keyword(user_text)
    images = robust_image_search(keyword)
    if images:
        for url in images[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์สำหรับคำค้น: {keyword}")
    else:
        send_message(chat_id, f"ขออภัย ไม่พบรูปภาพสำหรับ '{keyword}' จากทุกแหล่งครับ ลองเปลี่ยนรายละเอียดหรือระบุข้อมูลเพิ่มเติม เช่น ยี่ห้อ รุ่น สี ปี ฯลฯ")

# === handle message (ควบคุมทั้งรอบถาม+ภาพ) ===
def handle_message(data):
    message = data.get("message", {})
    chat_id = message["chat"]["id"]
    user_text = message.get("caption", "") or message.get("text", "")
    user_id = str(chat_id)

    # admin/owner ไม่ต้องนับ quota ถาม
    if user_id not in EXEMPT_USER_IDS:
        if not check_and_increase_usage(user_id, USAGE_FILE, MAX_QUESTION_PER_DAY):
            send_message(chat_id, f"ขออภัย คุณใช้งานครบ {MAX_QUESTION_PER_DAY} ครั้งแล้วในวันนี้")
            return

    # เงื่อนไข "ขอรูป"/image/etc (นับทั้ง 2 quota: ทั้งรอบถาม+รอบภาพ)
    if any(k in user_text.lower() for k in ["ขอรูป", "มีภาพ", "image", "picture", "photo", "รูป", "ภาพ"]):
        handle_image_search(chat_id, user_id, user_text)
    else:
        send_message(
            chat_id,
            "สอบถามภาพได้ทันทีโดยพิมพ์ 'ขอรูป...' หรือ 'มีภาพ...' ตามด้วยรายละเอียด เช่น 'ขอรูปยาง bridgestone 265/65R17 AT'"
        )
# ===== END =====
