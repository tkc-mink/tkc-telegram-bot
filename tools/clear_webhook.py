"""
📌 Script นี้ใช้สำหรับล้าง Webhook ออกจาก Telegram Bot
- ใช้เมื่อเปลี่ยนระบบจาก Webhook → Polling
- ใช้สำหรับแก้ไขกรณีบอทไม่ตอบเพราะ webhook เดิมค้างอยู่
- ควรใช้เฉพาะในขั้นตอน deploy หรือ debug

คำแนะนำ:
- ไม่ควรใช้ใน production ซ้ำโดยไม่จำเป็น
- ไม่ควรรันอัตโนมัติทุกครั้ง
"""

import requests
from config.tokens import BOT_TOKENS

for name, token in BOT_TOKENS.items():
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    response = requests.post(url)
    if response.status_code == 200:
        print(f"[{name}] ✅ ล้าง webhook สำเร็จ")
    else:
        print(f"[{name}] ❌ ล้มเหลวในการล้าง webhook: {response.text}")
