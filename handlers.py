# handlers.py

import os
import requests
from openai import OpenAI
from search_utils import fetch_google_images  # อ้างอิงฟังก์ชันจาก search_utils.py

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(chat_id, text):
    """
    ส่งข้อความ (text) ไปยังผู้ใช้ Telegram
    """
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )

def send_photo(chat_id, photo_url, caption=None):
    """
    ส่งรูป (จาก url) ไปยังผู้ใช้ Telegram
    """
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
        json=data
    )

def generate_image_search_keyword(user_text):
    """
    ใช้ GPT-4o ช่วยคิด 'คำค้น' สำหรับค้นรูป Google Images ที่มีโอกาสเจอรูปจริง
    """
    system_prompt = (
        "คุณคือ AI ที่เก่งเรื่องค้นหารูปจาก Google Images ให้คิด 'คำค้น' (search keyword) ที่เหมาะสมที่สุดจากโจทย์ของผู้ใช้ "
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

def handle_image_search(chat_id, user_text):
    """
    รับคำถาม user --> AI ช่วยคิด keyword --> ค้น Google Images --> ส่งรูปเข้า Telegram
    """
    keyword = generate_image_search_keyword(user_text)
    images = fetch_google_images(keyword)
    if images:
        for url in images[:3]:
            send_photo(chat_id, url, caption=f"ผลลัพธ์สำหรับคำค้น: {keyword}")
    else:
        send_message(chat_id, f"ขออภัย ไม่พบรูปภาพสำหรับ '{keyword}' ครับ ลองเปลี่ยนรายละเอียดหรือระบุข้อมูลเพิ่มเติม เช่น ยี่ห้อ รุ่น สี ปี ฯลฯ")

def handle_message(data):
    """
    ฟังก์ชันหลักสำหรับรับข้อความจาก Telegram (webhook/main.py ต้องเรียกทุกครั้งที่ได้รับ message)
    """
    message = data.get("message", {})
    chat_id = message["chat"]["id"]
    user_text = message.get("caption", "") or message.get("text", "")

    # เงื่อนไขเข้าสู่โหมดค้นหา "รูป" (AI ช่วยคิด keyword)
    if any(k in user_text.lower() for k in ["ขอรูป", "มีภาพ", "image", "picture", "photo", "รูป", "ภาพ"]):
        handle_image_search(chat_id, user_text)
    else:
        send_message(
            chat_id,
            "สอบถามภาพได้ทันทีโดยพิมพ์ 'ขอรูป...' หรือ 'มีภาพ...' ตามด้วยรายละเอียด เช่น 'ขอรูปยาง bridgestone 265/65R17 AT'"
        )

# หมายเหตุ: main.py หรือ webhook ต้องเรียก handle_message(data) ทุกครั้งที่มี message ใหม่เข้า Telegram
