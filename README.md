# tkc-telegram-bot

Telegram Bot สำหรับกลุ่มบริษัทตระกูลชัย (TKC Group)

ระบบนี้พัฒนาเพื่อใช้งานภายในองค์กร โดยให้พนักงานสามารถพูดคุยกับ GPT ผ่าน Telegram ในห้องแชท 1:1 ได้อย่างปลอดภัย พร้อมฟีเจอร์เสริมเพื่อสนับสนุนการทำงานจริง เช่น การรีวิวรายวัน, ระบบติดตามคำถาม, วิเคราะห์เทรนด์ และสำรองข้อมูลอัตโนมัติ

---

## 🔧 การติดตั้งเบื้องต้น

1. **Clone repository**
   ```bash
   git clone https://github.com/tkc-mink/tkc-telegram-bot.git
   cd tkc-telegram-bot
   ```

2. **สร้างไฟล์ `.env` จาก template**
   ```bash
   cp .env.example .env
   ```

3. **ติดตั้ง dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **รันบอท**
   ```bash
   python main.py
   ```

หรือหากต้องการรันผ่าน shell script:
   ```bash
   bash start.sh
   ```

---

## 🔑 ตัวแปรใน `.env`

ให้กรอกค่าตามรายละเอียดใน `.env.example` เช่น:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `AUTHORIZED_ADMINS` เป็นต้น

---

## 📁 โครงสร้างไฟล์

```
tkc-telegram-bot/
│
├── config/                # ไฟล์ตั้งค่าระบบ
├── tools/                 # ฟังก์ชันเสริม เช่น สำรอง/กู้คืน/จัดการข้อมูล
├── main.py                # จุดเริ่มต้นของโปรแกรมหลัก
├── requirements.txt       # รายชื่อไลบรารีที่ใช้
├── start.sh               # สคริปต์สำหรับรันโปรแกรม
├── .env.example           # ตัวอย่างไฟล์ ENV
└── README.md              # (ไฟล์นี้)
```

---

## 📌 หมายเหตุ

- ระบบนี้ออกแบบเฉพาะกลุ่มบริษัทตระกูลชัย
- มีระบบเก็บ log, ส่งรายงาน, วิเคราะห์แนวโน้ม และระบบลับบางส่วนเพื่อการดูแลพนักงาน

---

## 🛠 ผู้ดูแลระบบ

> คุณชลิต (@TKC_MINK) เป็นผู้ดูแลระบบเพียงผู้เดียวขององค์กรนี้

---
