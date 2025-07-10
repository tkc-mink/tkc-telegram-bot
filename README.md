
# TKC Telegram Bot

บอทตอบข้อความผ่าน Telegram โดยใช้ Flask + Gunicorn + Render

## ไฟล์ที่มี

- `main.py` – โค้ดหลักของ Flask
- `requirements.txt` – ไลบรารีที่ต้องติดตั้ง
- `render.yaml` – ไฟล์ config สำหรับ Render
- `.env.example` – ตัวอย่าง env

## วิธีใช้งาน

1. สร้าง `.env` และใส่ `BOT_TOKEN` จริงของคุณ
2. อัพขึ้น GitHub
3. Deploy ผ่าน Render เป็น Web Service
4. ตั้ง webhook:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-render-url.onrender.com/webhook
   ```

5. เสร็จสิ้น! บอทจะตอบข้อความเช่น "สวัสดี" ได้ทันที
