import os
import requests
from openai import OpenAI
from search_utils import robust_image_search  # ใช้ robust_image_search!

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

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

def handle_image_search(chat_id, user_text):
    keyword = generate_image_search_keyword(user_text)
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

    if any(k in user_text.lower() for k in ["ขอรูป", "มีภาพ", "image", "picture", "photo", "รูป", "ภาพ"]):
        handle_image_search(chat_id, user_text)
    else:
        send_message(
            chat_id,
            "สอบถามภาพได้ทันทีโดยพิมพ์ 'ขอรูป...' หรือ 'มีภาพ...' ตามด้วยรายละเอียด เช่น 'ขอรูปยาง bridgestone 265/65R17 AT'"
        )
