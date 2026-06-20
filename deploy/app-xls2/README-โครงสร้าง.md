# โครงสร้างโปรแกรมแก้ราคายาง (หลังแยกไฟล์ JS)

เอกสารนี้อธิบายว่า JS แต่ละไฟล์ทำอะไร โหลดลำดับไหน และ **กฎการแก้ไขที่ห้ามฝ่าฝืน** เพื่อไม่ให้โปรแกรมพัง

---

## 1) ลำดับการโหลด (สำคัญที่สุด — ห้ามสลับลำดับ)

`index.html` โหลดสคริปต์เป็น 5 กลุ่ม เรียงจากบนลงล่าง:

| กลุ่ม | ไฟล์ | หมายเหตุ |
|---|---|---|
| **A เครื่องยนต์/ไลบรารี** | `engine2.js`, `dbx-connect.js`, `sheet-grid.js`, `img-layer.js` ฯลฯ | สร้าง global หลัก: `XL2`, `SG`, `DBX`, `APIBridge`, `ImgLayer` ฯลฯ |
| **B ก่อนแกนหลัก** | `dialogs.js`, `filter-bar.js` | แกนหลักเรียกใช้ตอน init จึงต้องโหลด**ก่อน** |
| **C แกนหลัก** | `main-1-boot.js` → `main-7b-init.js` (10 ไฟล์) | **ต้องเรียงตามนี้** (ดูข้อ 3) |
| **D ฟีเจอร์เสริม** | `price-update.js`, `emoji-picker.js`, `backup-restore.js`, `theme.js`, `input-zoom.js` | เรียกแกนหลักผ่าน global ตอนผู้ใช้คลิก จึงโหลด**หลัง**ได้ |
| **E ท้ายสุด** | `sw-register.js` | ลงทะเบียน Service Worker |

### CSS (ใน `<head>`) — แยก 6 ไฟล์เช่นกัน
`xls2.css` เดิม (1,736 บรรทัด) ถูกแยกเป็น `css-01-base-grid.css` → `css-06-refinements.css`
โหลดด้วย `<link>` เรียง **01→06** · **ห้ามสลับลำดับ** (CSS cascade — ไฟล์หลังทับไฟล์ก่อนถ้า specificity เท่ากัน · เรียงเดิม = เหมือนไฟล์เดียวเป๊ะ)
ตัดเฉพาะที่ขอบ rule (depth 0) ไม่ตัดกลาง `{}`/`@media` · ไม่มี `@import`/`url()` จึงไม่มีปัญหา path
| ไฟล์ | เนื้อหา |
|---|---|
| `css-01-base-grid.css` | ฐาน + ribbon + fx/filter + ตาราง/เซลล์ |
| `css-02-windows.css` | หน้าต่างใหญ่ (Staging/Audit/กฎราคา/ผู้ใช้) |
| `css-03-pickers-dialogs.css` | ตัวเลือกสินค้า/สถานะ + แท็บ DB + ไดอะล็อก + อีโมจิ |
| `css-04-toolbar-misc.css` | เส้นขอบ + chatbot + ctx menu + status/file strip + modal + sidebar |
| `css-05-darkmode-images.css` | โหมดมืด + สี cf + แบรนด์ + API + รูปลอย/ตัดภาพ/AI |
| `css-06-refinements.css` | ปรับละเอียดหัว/ชื่อไฟล์ + dblink + เครื่องมือแถว2 + window chrome |

ลำดับกลุ่ม C (10 ไฟล์) ที่ถูกต้อง:
`1-boot → 2-more-menu → 3-view-mode → 4a-color-core → 4b-color-toolbar → 5-file-menu → 6a-settings → 6b-settings-tabs → 7a-sheet-file → 7b-init`

---

## 2) หน้าที่ของแต่ละไฟล์

**กลุ่ม B (โหลดก่อนแกน เพราะมี IIFE ของตัวเอง + เปิด global ที่แกนเรียกตอน init)**
- `dialogs.js` — `PopupStack`, `makeDraggable`, `AppDialog`, `alertDialog`, `confirmDialog`, `promptDialog`
- `filter-bar.js` — `renderFltBar` (แถบกรอง/ค้นหา)

**กลุ่ม C — แกนหลัก (เดิมคือ `app-main` ก้อนเดียว · ตอนนี้แตก 10 ไฟล์ แต่ยัง “แชร์ global scope เดียวกัน”)**
1. `main-1-boot.js` — บูต, `migrateSheets`, `SG.init`, แถบเครื่องมือจัดรูปแบบ, Ctrl+S/P, นิยาม `$` (global)
2. `main-2-more-menu.js` — เมนู ⋯ เครื่องมือเพิ่มเติม (จัดกลุ่ม + badge)
3. `main-3-view-mode.js` — สลับโหมดแอดมิน/ผู้ใช้ + ล็อกไฟล์ประวัติ
4. `main-4a-color-core.js` — เครื่องมือเลือกสีรวม `cfBuild` + จานเทสี/สีอักษร + `recentColors`
5. `main-4b-color-toolbar.js` — สีเส้นขอบ + ปุ่มเทสี/สีอักษร/เส้นขอบบนแถบ + `placePop` + `updBorderIcon`
6. `main-5-file-menu.js` — เมนูไฟล์ + บันทึกเป็น + เวอร์ชัน + modals
7. `main-6a-settings.js` — หน้าตั้งค่า: Margin/หัวตาราง/แถวพิเศษ/เชื่อมต่อ DB + `openSettings` + `switchSetTab` (มี forward-call `updDbSrcBadge` ภายใน → **แยกต่อไม่ได้**)
8. `main-6b-settings-tabs.js` — แท็บสำรอง/กู้คืน + กฎราคา/VAT + สีประจำแท็บ + ปุ่มลัดตั้งค่า
9. `main-7a-sheet-file.js` — แถบหมวด + ชื่อไฟล์ + เพิ่ม/แก้/ลบหมวด + กำหนดเวลา + `refresh()`
10. `main-7b-init.js` — เมนูโลโก้ + init ปิดท้าย (`refresh()`/`renderFltBar()`) + ออโต้เซฟ + เก็บแถบเครื่องมือ + เปิด `window.$/refresh/renderSheets`

**กลุ่ม D — ฟีเจอร์เสริม (แต่ละไฟล์เป็น IIFE ของตัวเอง + นิยาม `$` ของตัวเอง)**
- `price-update.js` — อัพเดทราคา (upd*) · เรียก `renderSheets`/`refresh` ผ่าน global
- `emoji-picker.js` — `openEmojiPicker` + ไอคอนกำหนดเอง
- `backup-restore.js` — สำรอง/กู้คืน .json ลงเครื่อง
- `theme.js` — โหมดมืด/สว่าง + สลับตอนพิมพ์
- `input-zoom.js` — ซูม + เม้าส์ Logitech

---

## 3) ทำไมแกนหลัก (กลุ่ม C) ต้องเรียงตามลำดับ และห้ามห่อ IIFE

แกนหลักเดิมเป็นฟังก์ชันก้อนเดียว (IIFE) ที่ใช้ตัวแปร/ฟังก์ชันร่วมกันผ่าน closure
ตอนแยก เรา **ถอด IIFE ออก (de-IIFE)** ทำให้ทุกสัญลักษณ์ทั้ง 112 ตัวกลายเป็น **global** —
ตรวจแล้วว่าไม่มีชื่อชนกับ built-in ของ `window` (name/top/open/close/status/length ฯลฯ)

ผลคือทุกไฟล์ในกลุ่ม C ยัง “อยู่สโคปเดียวกัน” ผ่าน global scope · จุดตัดเลือกไว้ที่ขอบคำสั่งระดับบนสุด
และตรวจแล้วว่า **ไม่มีการเรียกฟังก์ชันตอนโหลดข้ามไฟล์ไปข้างหน้า** (forward-call) ที่จะพังเพราะ hoisting ไม่ข้ามไฟล์

### กฎเหล็ก (ฝ่าฝืน = พัง)
1. **ห้ามสลับลำดับ** กลุ่ม C (1 → 2 → 3 → 4a → 4b → 5 → 6a → 6b → 7a → 7b) และห้ามย้ายไปก่อนกลุ่ม B
2. **ห้ามห่อไฟล์ใดในกลุ่ม C ด้วย `(function(){…})()` ใหม่** — จะตัดทุกอย่างออกจาก global scope ทันที
3. **ห้ามแยก `main-6a-settings.js` ต่อ** — มี forward-call `updDbSrcBadge()` (เรียกก่อนนิยามภายในไฟล์ อาศัย hoisting)
4. เพิ่มฟังก์ชัน/ตัวแปรที่ไฟล์อื่นในกลุ่ม C ต้องใช้ → ประกาศเป็น top-level (`var`/`function`) ในไฟล์ใดก็ได้ของกลุ่ม C มันจะเป็น global อัตโนมัติ
5. ถ้าจะเพิ่ม **ฟีเจอร์เสริมใหม่** ที่เรียกแกนแค่ตอนคลิก → ทำเป็นไฟล์ IIFE แยก นิยาม `$` ของตัวเอง วางในกลุ่ม D

---

## 4) วิธีเพิ่มฟีเจอร์เสริมใหม่ (เทมเพลตปลอดภัย)

```js
/* my-feature.js — โหลดในกลุ่ม D (หลังแกนหลัก) */
(function () {
  var $ = function (id) { return document.getElementById(id); };
  // เรียกแกนผ่าน global ได้เลย: SG, XL2, refresh(), renderSheets(), confirmDialog() ฯลฯ
  $('btnMyThing').onclick = function () { /* ... */ refresh(); };
})();
```
แล้วเพิ่มแท็กในกลุ่ม D ของ `index.html`

---

## 5) เช็กลิสต์ทดสอบหลังแก้ (กันพัง)

วิธีเร็ว: เปิด **`smoke-test.html`** (อยู่ที่รากโปรเจกต์) → รันทดสอบ 27 ข้ออัตโนมัติ ถ้าขึ้น “✅ 27/27 ผ่าน” แปลว่าโครงสร้างยังดี (มีปุ่ม “↻ รันใหม่”)

หรือตรวจด้วยมือ — เปิดหน้าเว็บแล้วดู Console ต้องไม่มี error และลอง:
- ตารางขึ้นครบ · แถบกรองทำงาน
- เมนู ⋯ / สลับโหมด / popup สี-เส้นขอบ
- เปิดหน้าตั้งค่า (⚙️) แล้วทุกแท็บมี grid สี
- อัพเดทราคา (🔄 ⏱) / เวอร์ชัน / กำหนดเวลา
- บันทึก (Ctrl+S) แล้วสถานะเปลี่ยนเป็น “บันทึกแล้ว”
