# TKC Telegram Bot

ระบบบอทสำหรับพนักงานของกลุ่มบริษัทตระกูลชัย  
เวอร์ชันนี้ใช้ `BOT_TOKEN_SHIBANOY` ตัวเดียวเพื่อความง่ายในการเริ่มต้นใช้งาน

## 📦 โครงสร้าง

- `main.py` — จุดเริ่มต้นของโปรแกรม
- `config/tokens.py` — โหลดค่า Token และ API Key
- `tools/Profile` — โปรไฟล์ของระบบ
- `.env.example` — ตัวอย่าง ENV
- `start.sh` — สคริปต์รันง่าย
- `requirements.txt` — ไลบรารีที่ต้องใช้

## 🚀 วิธีใช้งาน

```bash
cp .env.example .env
# จากนั้นแก้ไขค่า token ให้ถูกต้อง

bash start.sh
```
