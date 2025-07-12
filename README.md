# TKC Telegram Bot (ขั้นตอนที่ 1)

ระบบบอทที่สามารถตอบข้อความบน Telegram ได้ทันทีผ่าน Webhook

## วิธีใช้งาน
1. ติดตั้ง dependencies:
   ```
   pip install -r requirements.txt
   ```

2. ตั้งค่าข้อมูลใน `.env`

3. รัน Flask ด้วย Gunicorn (ใช้กับ Render):
   ```
   gunicorn main:app
   ```

4. รัน `set_webhook.py` หนึ่งครั้งเพื่อเชื่อม Webhook:
   ```
   python set_webhook.py
   ```

## ทดสอบ
- พิมพ์ `/start` → จะได้ข้อความต้อนรับ
- พิมพ์อะไรก็ได้ → บอทจะตอบกลับเหมือน echo

พร้อมต่อยอดเชื่อม GPT ในขั้นตอนถัดไป