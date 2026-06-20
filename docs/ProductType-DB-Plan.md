# แผนระบบ "ชนิดสินค้า" + เชื่อม Database (server local)

> เอกสารออกแบบ/วางแผน สำหรับ DYNAMIC PRICE LIST — โมดูล `ProductInfo` (app-xls2/product-info.js)
> อัปเดต: มิ.ย. 2026

## 1. สรุปสถานะปัจจุบัน (ทำแล้วในรอบนี้)

### ✅ เพิ่มชนิดสินค้าเองได้
- เดิมมีชนิดในตัว: ยาง 🛞 · ยางใน ⭕ · ยางรอง 🔘 · กระทะ ⚙️ · คิ้ว ✨ · แบต 🔋 · น้ำมัน 🛢️ · อื่นๆ 📦
- ตอนนี้แอดมินกด **"เปลี่ยนชนิด" → "➕ เพิ่มชนิดใหม่…"** ได้ในป๊อปอัปรายละเอียดสินค้า
  - ตั้ง **ไอคอน + ชื่อชนิด** + **ช่องข้อมูล (ฟิลด์)** เองได้ เช่น "โซ่รถ ⛓️" ฟิลด์ "ขนาด, ความยาว"
  - ลบชนิดที่สร้างเองได้ (ชนิดในตัวลบไม่ได้)
- เก็บใน `store.customTypes` (localStorage) — โครงสร้างเดียวกับชนิดในตัว

### ✅ สวิตช์แหล่งข้อมูล (scaffold)
- `ProductInfo.getSourceMode()` / `setSourceMode('manual' | 'database')`
- UI: ในหน้า "เปลี่ยนชนิด" (เฉพาะแอดมิน) มีปุ่ม **⚙️ กำหนดเอง · 🗄️ ฐานข้อมูล**
- **manual** (ดีฟอลต์) = ใช้ค่าที่กำหนดในเครื่องนี้เท่านั้น ไม่ดึง/ไม่ทับจากส่วนกลาง
- **database** = ดึงจาก server local อัตโนมัติ (ผ่าน `syncPull` ที่มีอยู่) + รีเฟรชเมื่อสลับโหมด

## 2. สถาปัตยกรรมข้อมูล

```
┌─────────────────┐      syncPush(adminKey)      ┌──────────────────────┐
│  เครื่องแอดมิน    │ ───────────────────────────▶ │  Server local        │
│  (localStorage)  │ ◀─────────────────────────── │  (Registry / Worker) │
└─────────────────┘      syncPull (ทุก session)   └──────────────────────┘
        │                                                    │
        │ manual mode = ไม่ยุ่งกับ server                      │ database mode = แหล่งจริง
        ▼                                                    ▼
   ใช้ค่าในเครื่อง                                      ทุกเครื่องเห็นชุดเดียวกัน
```

ชั้นเชื่อมต่อมีอยู่แล้ว (ยังไม่ผูก server จริง):
- `ProductInfo.exportData()` → ก้อน JSON ({type, dims, fields, alias, customTypes})
- `ProductInfo.importData(d, replace)` → รวมเข้ากับของในเครื่อง
- `ProductInfo.syncPull()` → เรียก `Registry.prodInfoGet()`
- `ProductInfo.syncPush(adminKey, by)` → เรียก `Registry.prodInfoSet()`

## 3. สิ่งที่ต้องทำต่อ (เมื่อเชื่อม server จริง)

### 3.1 ฝั่ง Server (local / Worker)
- [ ] Endpoint `GET /prodinfo` → คืน `{ok, data, rev, updatedAt}`
- [ ] Endpoint `POST /prodinfo` (ต้องมี adminKey) → บันทึก + เพิ่ม `rev`
- [ ] เก็บ **เวอร์ชัน (rev)** กันเขียนทับกัน (optimistic lock)
- [ ] (อนาคต) ผูกกับฐานข้อมูลสินค้าจริง (รหัสสินค้า ↔ ชนิด/สเปก/สต็อก/DOT)

### 3.2 ฝั่งแอป
- [x] ผูก `window.Registry.prodInfoGet/Set` (มี `device-registry-client.js` ต่อ Cloudflare Worker อยู่แล้ว — เหลือตั้ง URL)
- [x] **database mode**: ค่าจาก server "ทับ" ค่าในเครื่อง — `importData(d,'override')` (server ชนะรายคีย์ แต่คงคีย์ที่มีเฉพาะในเครื่อง) · `syncPull` เลือกโหมดอัตโนมัติตาม sourceMode
- [x] ปุ่ม **"⬇️ ดึงส่วนกลาง"** (syncPull) + **"⬆️ บันทึกขึ้นส่วนกลาง"** (syncPush) ในแท็บ 📐 ขนาด/สินค้า
- [x] สวิตช์ **⚙️ กำหนดเอง · 🗄️ ฐานข้อมูล** + เตือนเมื่อยังไม่ตั้ง URL server
- [ ] เพิ่ม **rev/สถานะซิงก์** (ล่าสุดเมื่อไร · เลขเวอร์ชัน) — รอ endpoint คืน `rev`
- [ ] จัดการ **ขัดแย้ง (conflict)**: ถ้า local แก้หลัง pull → เตือนก่อน push ทับ (รอ rev)

### 3.3 กติกาการตัดสิน (manual vs database)
| โหมด | อ่านค่า | เขียนค่า | ซิงก์อัตโนมัติ |
|---|---|---|---|
| **manual** | ในเครื่อง | ในเครื่อง | ไม่ |
| **database** | server (fallback เครื่อง) | ในเครื่อง + เตือนให้ push | pull ทุก session |

> หลักการ: **database = แหล่งความจริง (source of truth)** · manual = ทำงานออฟไลน์/อิสระต่อเครื่อง

## 4. ความเสี่ยง / ข้อควรระวัง
- ข้อมูลตอนนี้เก็บ **per-device** (localStorage) → ถ้าไม่ push ขึ้น server เครื่องอื่นไม่เห็น
- การ override จาก server ต้องทำหลังยืนยัน rev เพื่อกัน "ของหาย"
- adminKey สำหรับ push ต้องเก็บปลอดภัย (อย่าฝังในหน้าเว็บ public)
- ชนิดที่สร้างเอง (customTypes) ก็อยู่ในก้อน sync ด้วย → ต้อง push ถึงจะใช้ร่วมทั้งร้าน

## 5. ลำดับงานแนะนำ
1. ตั้ง server local + 2 endpoint (get/set) พร้อม rev
2. ผูก `Registry.prodInfoGet/Set`
3. เพิ่ม override-by-rev ใน database mode + สถานะซิงก์
4. ปุ่ม push/pull manual + เตือน conflict
5. (เฟสถัดไป) เชื่อมรหัสสินค้าเข้ากับฐานข้อมูลสต็อก/DOT — ต่อยอดจาก ROADMAP-DOT-DB.md
