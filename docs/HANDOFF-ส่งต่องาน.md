# 📋 เอกสารส่งต่อ — แอป "แก้ราคายาง" (TKC Dynamic Price List)
> อ่านไฟล์นี้ไฟล์เดียวก็ต่องานได้ทันทีในแชทใหม่ · อัปเดตล่าสุด: รอบที่ทำ Cloudflare device-registry Worker เสร็จ

---

## 0) สรุปสั้นสุด (TL;DR)
แอป spreadsheet จัดการราคายาง (ภาษาไทย, vanilla JS, ไม่มี build step, เป็น PWA) ที่:
- **แยกไฟล์ JS/CSS เป็นโมดูลครบแล้ว** (`index.html` เป็น HTML ล้วน)
- **ต่อ API ราคาจริง** (PHP ผ่าน ngrok) ได้แล้ว — อ่านอย่างเดียว ยังไม่เขียนกลับ
- มี **ออฟไลน์ snapshot + เข้ารหัส + login/PIN + auto-logout + remote wipe + PWA**
- เพิ่งเขียน **Cloudflare Worker ทะเบียนกลางอุปกรณ์ (OTP/log/revoke)** เสร็จ — **ยังไม่ต่อฝั่งแอป**
- มี **smoke test 30/30** เป็นตาข่ายกันพัง (เปิด `smoke-test.html`)

**กฎเหล็กตลอดโปรเจกต์:** ห้ามพัง · ทุกครั้งที่แก้เสร็จต้องผ่าน smoke test 30/30 · **ยังไม่ deploy จนกว่าจะสั่ง**

---

## 1) สถาปัตยกรรมไฟล์ (สำคัญ — อ่านก่อนแก้)

`index.html` = HTML + แท็ก `<script>`/`<link>` ล้วน ไม่มี inline JS/CSS แล้ว
โหลด JS เป็น 5 กลุ่ม (รายละเอียดเต็มใน `app-xls2/README-โครงสร้าง.md`):

| กลุ่ม | ไฟล์ | กฎ |
|---|---|---|
| A เครื่องยนต์ | `engine2.js`, `sheet-grid.js`, `db-staging.js`, `dbx-connect.js`, `data-pickup01.js` ฯลฯ | สร้าง global: `XL2`, `SG`, `DBX` |
| B ก่อนแกน | `dialogs.js`, `filter-bar.js` | แกนเรียกตอน init → ต้องมาก่อน |
| **C แกนหลัก (10 ไฟล์)** | `main-1-boot.js` → `main-7b-init.js` | **ห้ามสลับลำดับ · ห้ามห่อ IIFE · ห้ามแยก main-6a (มี forward-call updDbSrcBadge)** |
| D ฟีเจอร์เสริม | `price-update.js`, `emoji-picker.js`, `backup-restore.js`, `theme.js`, `input-zoom.js`, `auth.js`, `device-id.js`, `auto-logout.js` | IIFE แยก นิยาม `$` เอง · เรียกแกนผ่าน global |
| E ท้ายสุด | `sw-register.js` | ลงทะเบียน Service Worker |

**CSS:** `xls2.css` เดิมแยกเป็น `css-01-base-grid.css` → `css-06-refinements.css` โหลด `<link>` เรียง 01→06 (**ห้ามสลับ — cascade**)

### วิธีแก้แบบไม่พัง
- แกนหลัก (กลุ่ม C) เป็น **de-IIFE** → ทุกสัญลักษณ์เป็น global โดยตั้งใจ (เช็กแล้วไม่ชน built-in)
- เพิ่มฟีเจอร์ใหม่ที่เรียกแกนแค่ตอนคลิก → ทำเป็นไฟล์ IIFE แยก วางกลุ่ม D
- **แก้เสร็จทุกครั้ง → เปิด `smoke-test.html` ต้องเขียว 30/30**

---

## 2) สิ่งที่ทำเสร็จแล้ว (✅)

### ฟีเจอร์ราคา/DOT
- คอลัมน์ผูกฟิลด์ DB (คลิกขวาหัวคอลัมน์ในโหมดแอดมิน)
- **ปียาง DOT (ช่วงปี + ลงสีตามอายุ)**: แสดงช่วง "22-26" สองโทน · ดำ=ปีล่าสุด เขียว=เก่า1ปี แดง=เก่า≥2ปี · DF prefix (deflect) · clamp ปีอนาคต/ทศนิยม · ปีปัจจุบันเลื่อนอัตโนมัติ
- **popup ราคาแยกราย DOT**: เด้งเมื่อมี DOT >1 ชุด · ตาราง DOT/จำนวน/ราคา ขาย-B-A-S · แอดมินกรอกได้ (prefill จากแถวหลัก) · ผู้ใช้เห็นเป็นโค้ด cipher · เก็บในเครื่องเท่านั้น · qty 0 ลบอัตโนมัติ · พิมพ์แบบ Excel (Enter/ลูกศรนำทาง → ปุ่มบันทึก)
- ตั้งค่าสี/ขนาด/ความหนาตัวเลข DOT + ราคา popup ครบ (แท็บ "🛞 สีปียาง (DOT)")
- แผงรายละเอียดสินค้า: รูป (สูงสุด 4) · 🚚 ของกำลังเข้า (จำนวน/วันที่สั่ง/สถานะ) + popup ซ้อน + ลิงก์ไปตั้งค่า DB

### โครงสร้าง/คุณภาพ
- แยก JS 17+ ไฟล์ · CSS 6 ไฟล์ · `index.html` 2,680→~640 บรรทัด
- `smoke-test.html` (30 ข้อ) · `README-โครงสร้าง.md`
- ไอคอนแชท = ชิบะอินุใส่แว่น+หูฟัง call center
- ไอคอนสถานะเปลี่ยนชื่อ/สี/ไอคอนได้ปลอดภัย (ผูกด้วย cond ไม่ใช่ชื่อ) + ตัวบ่งชี้ 🔗 ฟิลด์ที่ผูก
- header จัดระเบียบ/กระชับ · badge "LIVE/Mock" · จัดเรียงปุ่มตั้งค่า

### ต่อ API จริง (อ่านอย่างเดียว)
- `db-staging.js` มี **MockAdapter** (ปัจจุบัน) + **HttpAdapter** (ต่อ server จริง)
- ตั้งค่า → เชื่อมต่อ DB → "เซิร์ฟเวอร์จริง" → กรอก Base URL + Authorization token + user/pass/Flag → ทดสอบ → บันทึก
- API: `FLAG=PRICE` ส่ง header `Authorization/Flag/Username/Password` + `ngrok-skip-browser-warning` · map `ID`→รหัส, `PRICE1-5`→ราคา · cache 60 วิ
- **ข้อมูลที่ API ส่ง = ราคาเท่านั้น** (ชื่อ/สต็อก/DOT ยังเป็น mock — รอ Flag อื่น)
- ⚠️ ถ้าเจอ CORS ต้องเพิ่ม header ฝั่ง PHP (Access-Control-Allow-Origin/Headers)

### ความปลอดภัย/ออฟไลน์ (ในเครื่อง)
- **Snapshot + fallback อัตโนมัติ**: ดึง API สำเร็จ→เก็บราคาลงเครื่อง · server ล่ม→ใช้ราคาล่าสุดต่อได้
- **เข้ารหัส snapshot (AES-GCM)** ด้วยกุญแจจาก PIN
- **`auth.js`**: login + PIN พนักงาน (SHA-256+salt) · `Auth.unlockKey()` = กุญแจเข้ารหัส · session-based
- **`auto-logout.js`**: ไม่ใช้งานครบเวลา (default 5 นาที) → ล็อก ต้อง PIN ใหม่ · shared=เปิด bound=ปิด
- **remote wipe**: (ตรวจสถานะจาก server → ล้างข้อมูลในเครื่อง)
- **`device-id.js`**: `DeviceID` (รหัส 32 หลักคงที่ + ชื่อ/ประเภท shared|bound) + `UsageLog` (เก็บวน 500)
- เก็บเฉพาะราคา ไม่มีทุน (data-minimization)
- **PWA**: `sw.js` + manifest → ติดตั้ง/ออฟไลน์ได้

---

## 3) งานที่กำลังทำ/ค้าง — ระบบทะเบียนกลางอุปกรณ์ (🔨 ครึ่งทาง)

### ✅ ทำเสร็จ: Cloudflare Worker (ฝั่ง server)
ไฟล์ `cloudflare-worker/device-registry.js` — ทะเบียนกลาง เปิดตลอด 24 ชม. ใช้ KV
**Actions:** `OTP_REQUEST` · `OTP_VERIFY` · `DEVICE_CHECK` · `LOG_PUSH` · `DEVICE_LIST`(admin) · `DEVICE_REVOKE`(admin) · `LOG_LIST`(admin)
- OTP 6 หลัก อายุ 3 นาที · รหัสโผล่ใน DEVICE_LIST (pending) ให้แอดมินอ่าน
- "ลบแล้วเข้าไม่ได้อีก" กันข้ามเครื่องจริง (token อยู่บน server)
- ต้องตั้ง: KV binding ชื่อ `REGISTRY` + env `ADMIN_KEY` (คำแนะนำติดตั้งอยู่หัวไฟล์)

### ⏭️ ยังไม่ทำ: ฝั่งแอป (client) — งานรอบหน้า
1. **`device-registry-client.js`** (ไฟล์ IIFE ใหม่ กลุ่ม D) — wrapper เรียก Worker:
   `Registry.otpRequest()` / `otpVerify(code)` / `check()` / `pushLog(event)` / (admin) `list()` / `revoke(id)`
   - เก็บ token จาก OTP_VERIFY ลงเครื่อง · ใช้ `DeviceID.get()` เป็น deviceId · URL เก็บใน config
2. **หน้า OTP ลงทะเบียนครั้งแรก** — เปิดแอปครั้งแรกบนเครื่องใหม่ → ขอ OTP → ใส่รหัส → ได้ token
3. **`DEVICE_CHECK` ตอน boot** — ถ้า `revoked` → ล้าง session + ขึ้นหน้า "อุปกรณ์ถูกเพิกถอน"
4. **หน้าแอดมินจัดการอุปกรณ์** — list อุปกรณ์/คำขอ pending (เห็นรหัส OTP) · ปุ่ม revoke · ดู log
   - **หมายเหตุ:** ตกลงกันว่า **ADMIN เป็นคนละโปรแกรม/แชทแยก** — หน้าแอดมินนี้อาจอยู่ในแอป ADMIN ใหม่
5. **permission ระดับ USER** — ❓ ยังรอ requirement: แอดมินกำหนดสิทธิ์ระดับไหน/ทำเป็นกลุ่มสิทธิ์ไหม

### 🔜 ส่วนเสริมที่ยังค้าง (ไม่กระทบความปลอดภัยหลัก)
- ป้ายอายุข้อมูล snapshot ("ใช้ราคาล่าสุด เก่า X ชม.")
- ย้าย snapshot ไป IndexedDB (รองรับหมื่น SKU) + ดัชนีค้นหาในเครื่อง
- ปุ่ม "จำลอง (Mock)" สร้างชุดใหม่ — ทำแล้วแต่ **ยังไม่ยืนยันด้วยตาว่าตัวเลขเปลี่ยนจริง** (อาจมี cache ค้าง — งานเล็ก ไล่ปิด cache)

---

## 4) API จริง — ข้อมูลเชื่อมต่อ (PHP ผ่าน ngrok)
- Base URL ตัวอย่าง: `https://<id>.ngrok-free.app/API_MINK/` (⚠️ ngrok = เปิดเฉพาะตอนเครื่องเปิด · URL เปลี่ยนเมื่อรีสตาร์ท)
- Headers: `Authorization: <token>` · `Flag: PRICE` (หรือ `XLOGIN`=ดึง user/pass) · `Username` · `Password` · `ngrok-skip-browser-warning: true`
- Response: JSON มี `ID`, `PRICE1..5` (ฟิลด์อื่นรอ server เพิ่ม)
- **secret ทั้งหมดเก็บในหน้าตั้งค่า (localStorage) ไม่ฝังในโค้ด**
- รายละเอียดเต็ม + โมเดล write-back รายเส้น: `docs/ROADMAP-DOT-DB.md`

---

## 5) เอกสารอื่นในโปรเจกต์ (อ่านเพิ่ม)
- `app-xls2/README-โครงสร้าง.md` — แผนที่ไฟล์ + กฎเหล็ก + เทมเพลตเพิ่มฟีเจอร์
- `docs/ROADMAP-DOT-DB.md` — สเปก API, สัญญาข้อมูล, แผน Mock→จริง, write-back, ผูกฟิลด์สถานะ
- `docs/OFFLINE-FALLBACK.md` — แผนสำรองออฟไลน์ 5 ชั้น
- `docs/DEVICE-LOG-OTP-PLAN.md` — สเปก endpoint อุปกรณ์/OTP/log
- `cloudflare-worker/device-registry.js` — Worker ทะเบียนกลาง (คำแนะนำติดตั้งในไฟล์)

---

## 6) วิธีเริ่มงานในแชทใหม่ (แนะนำ)
1. บอก AI ให้อ่านไฟล์นี้ + `README-โครงสร้าง.md` ก่อน
2. ระบุงาน เช่น "เขียน `device-registry-client.js` + หน้า OTP ต่อ Worker ที่ deploy แล้ว URL=..."
3. **ก่อนเริ่ม:** deploy Worker + ทดสอบ `OTP_REQUEST` ผ่าน แล้วแจ้ง URL
4. **ตอบ permission ของ USER** (ข้อ 3.5) ถ้าจะทำหน้าแอดมิน
5. ทุกครั้งที่แก้เสร็จ → smoke test 30/30 → **ยังไม่ deploy จนกว่าจะสั่ง**

### environment ที่ควรรู้
- vanilla JS ล้วน ไม่มี framework/build · ภาษาไทยทั้งแอป
- มี `deploy/` + `deploy-update/` (สำเนาสำหรับ deploy — มี app-xls2 ของตัวเอง อย่าลืม sync ตอน deploy)
- push GitHub ได้ (เคยทำ) · screenshot ในเครื่อง AI บางทีขัดข้อง → ตรวจด้วย eval_js/computed styles แทน
