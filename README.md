# TKC Telegram Bot (Webhook-based)

ระบบ Telegram Bot สำหรับกลุ่มตระกูลชัย  
เชื่อมต่อด้วย Webhook (Flask) พร้อมใช้งานบน Render

## วิธีใช้งาน

1. สร้างไฟล์ `.env` และใส่:
```
BOT_TOKEN=xxxxxxxxxxxxxxxxxxxx
APP_URL=https://your-render-url.onrender.com
```

2. ติดตั้ง lib และรันบอท:
```
pip install -r requirements.txt
python main.py
```

## วิธี Deploy บน Render
- ใช้ไฟล์ `render.yaml`
- เพิ่ม Environment Variables:
  - BOT_TOKEN
  - APP_URL
