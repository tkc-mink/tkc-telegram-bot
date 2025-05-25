import os
from dotenv import load_dotenv

load_dotenv()  # โหลดค่าจากไฟล์ .env อัตโนมัติ

BOT_TOKENS = {
    "shibanoy": "7517424701:AAEkE7bmCy-v7wR4esVJRuDX8tkeyiquSSI",
    "giantjiw": "7660238907:AAE5mAE0XZqcWdEn2kMFlTR8un94d4oRLwk",
    "p_tyretkc": "8029492335:AAERvbsWOojRul0y1u1ZYwjFdyT7smp5U8E",
    "tex_speed": "7426078648:AAEsTxPG37VqO8m61YeC3OVOfLVvvypwQw8"
}

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
