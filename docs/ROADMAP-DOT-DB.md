# แผนโครงสร้างระยะยาว — DOT · ราคา · เชื่อมต่อฐานข้อมูล (Roadmap)

เอกสารนี้วางโครงสร้างฟีเจอร์ที่เกี่ยวกับ **ปียาง (DOT)**, **ราคาแยกราย DOT**, **สถานะสินค้า/ของกำลังเข้า** และการ **เชื่อมต่อฐานข้อมูลจริง** เพื่อให้ต่อยอดได้ในอนาคตโดยไม่ต้องรื้อ

---

## 1) ภาพรวมสถาปัตยกรรมปัจจุบัน

```
ตาราง (sheet-grid.js)
  ├─ คอลัมน์ผูกฟิลด์ DB  doc.columnMap[c] = { field, mode }
  ├─ แถวผูกสินค้า        doc.rowLinks[r] = code13
  └─ ดึงข้อมูลผ่านชั้นกลาง  window.DBX  (db-staging.js)

ชั้นกลางข้อมูล (DBX — db-staging.js)
  ├─ adapter: Mock | Http     ← สลับได้ (DBX.setAdapter)
  ├─ FIELDS[]                 ← แคตตาล็อกฟิลด์ที่ผูกคอลัมน์ได้
  ├─ batchClean(codes) → toClean(raw)   ← normalize เป็น "clean model"
  └─ computeStatus(p)         ← คำนวณไอคอนสถานะ (หมด/จอง/ของเข้า/ฯลฯ)

โมดูลฟีเจอร์ (แยกไฟล์ · เปิด global)
  ├─ dot-year.js   DOT ช่วงปี + DF + สีตามอายุ + popup ราคาแยก DOT (เก็บ local)
  ├─ dialogs.js    PopupStack / AppDialog
  └─ … (price-update, emoji, backup, theme ฯลฯ)
```

**หลักการที่ยึดไว้:** UI ดึงข้อมูลผ่าน `DBX` เท่านั้น ไม่แตะ adapter ตรง → สลับจาก Mock เป็น API จริงได้โดยไม่แก้ UI

---

## 2) สัญญาข้อมูล (Data Contract) — ฟิลด์ที่ DB จริงต้องส่ง

โครงสร้าง "clean model" ต่อสินค้า 1 ตัว (จาก `toClean`):

| ฟิลด์ | ชนิด | ใช้ที่ | หมายเหตุ |
|---|---|---|---|
| `code13` | string(13) | คีย์หลัก | |
| `name`, `brandCode`, `size`, `model`, `spec` | string | แสดง/ค้นหา | |
| `costStandard/Average/Latest` | number | cipher #1 | **ห้ามส่งเป็นโค้ด — ส่งเลขจริง** |
| `salePrice1..5` | number | ราคา (เขียนกลับได้เฉพาะ 1–5) | cipher #2 ตอนแสดง |
| `qtyOnHand`, `qtyReserved`, `qtyAvailable` | number | สต็อก/สถานะ | |
| `incoming` | number | ของกำลังเข้า (จำนวน) | |
| `incomingInfo` | `{ orderedAt:ts, status:'ordered'\|'receiving', eta? }` | popup ของเข้า | **ขยายได้:** เลข PO, ผู้ขาย, ล็อต |
| `dotWeeks[]` | `{ dot:yy, week, qty, df?:bool }` | คอลัมน์ DOT + popup ราคา | `df:true` = ยางเกิด deflect · `qty` = สต็อกของชุดนั้น |
| `flags` | `{ needsWithdraw, special, … }` | สถานะ/เงื่อนไขแสดง | |
| `images[]` | `{ url }` | แกลเลอรี (สูงสุด 4) | |

> **กฎเหล็ก:** ราคา/ทุนจริงอยู่ใน DB เสมอ · cipher ใช้ตอน "แสดง" เท่านั้น · server ห้ามส่งโค้ดแทนเลข (อ้าง CLAUDE.md)

---

## 3) ราคาแยกราย DOT — ที่เก็บและทิศทางอนาคต

**ปัจจุบัน:** เก็บใน `localStorage['xls2_dotprices']` = `{ code13: { dotKey: {retail,b,a,s} } }`
- `dotKey` = ปี (เช่น `"24"`) หรือ `"DF"`
- ราคาแถวหลัก (ขาย/B/A/S คอลัมน์ 7/13/16/19) = ราคาปีปัจจุบัน → **เขียนกลับ DB ได้**
- ราคาราย DOT (ปีเก่า/DF) = **เฉพาะในเครื่อง ไม่เขียนกลับ DB**

**อนาคต (เมื่อมี API):**
- เพิ่ม endpoint `GET/PUT /api/pricelist/dot-prices/{code13}` เก็บราคาราย DOT ฝั่ง server (per สาขา/ผู้ใช้)
- ย้าย logic อ่าน/เขียนจาก `localStorage` → `DBX.getDotPrices/saveDotPrices(code, map)` (ชั้นกลางเดิม สลับ Mock/Http)
- ชุดที่ขายหมด (qty 0) ลบทิ้งอัตโนมัติ (มีแล้วใน `pruneSold`) — ฝั่ง server ทำ housekeeping เดียวกัน

---

## 4) เชื่อมต่อฐานข้อมูลจริง — ขั้นตอนเปลี่ยนจาก Mock → API

1. เขียน `HttpAdapter` (เลียน interface ของ `MockAdapter`: `search/get/batch/pushPrices`)
2. ตั้งค่าใน **ตั้งค่า → เชื่อมต่อ DB**: `baseUrl`, `token`, `useAuth` (เก็บที่ `DBX.setConfig`)
3. สลับ adapter: `DBX.setAdapter(HttpAdapter(config))` เมื่อ `config.adapter === 'http'`
4. UI ไม่ต้องแก้ — ดึงผ่าน `DBX.batchClean` เหมือนเดิม
5. การเขียนกลับ: เฉพาะ `salePrice1..5` ผ่าน `DBX.pushPrices` + เขียน `audit_log` ทุกครั้ง

**ลิงก์ในแอป:** popup "ของกำลังเข้า" และจุดที่เกี่ยวกับ DB มีลิงก์ → เปิด **ตั้งค่า → เชื่อมต่อ DB** (`openSettings('dbconn')`) เพื่อให้ผู้ใช้ตั้งค่าการเชื่อมต่อได้จากตรงนั้น

---

## 5) สถานะสินค้า / ของกำลังเข้า — แผนขยาย

- ปัจจุบัน `computeStatus(p)` คำนวณไอคอนจาก qty/flags · แก้นิยาม/สีได้ที่ **ตั้งค่า → ไอคอนสถานะ**
- ไอคอน 🚚 ของกำลังเข้า → คลิกเปิด popup รายละเอียด (วันที่สั่ง/สถานะ) ซ้อนเหนือแผง · ไอคอนที่ไม่ลิงก์ DB ไม่มี popup
- **อนาคต:** ผูก `incomingInfo` กับระบบ PO จริง (เลขใบสั่งซื้อ, ผู้ขาย, ETA, ติดตามขนส่ง) — โครงสร้าง popup รองรับการเพิ่มฟิลด์โดยไม่ต้องรื้อ

---

## 6) จุดต่อขยาย (Extension Points) — แก้ตรงไหนเมื่ออยากเพิ่ม

| อยากเพิ่ม | แก้ที่ |
|---|---|
| ฟิลด์ DB ใหม่ผูกคอลัมน์ได้ | `db-staging.js → FIELDS[]` (+ resolver ใน `dbFieldVal` ถ้าเป็นค่าคำนวณ) |
| กติกาแสดง DOT / สี | `dot-year.js` (cellModel/cellHTML + แท็บตั้งค่า "สีปี DOT") |
| สถานะ/ไอคอนใหม่ | `DEFAULT_STATUS_DEFS` + `computeStatus` |
| รายละเอียด popup ของเข้า | `showIncomingPopup` (sheet-grid.js) + `incomingInfo` |
| สี popup ทั้งระบบ | ตัวแปร `--pop-bg/--pop-fg` + คลาส `body.pop-bg/pop-fg` (css-06) |

---

## 7) สิ่งที่ควรทำต่อ (ลำดับแนะนำ)
1. ทำ `HttpAdapter` + endpoint อ่านสินค้า (read-only) ก่อน → ใช้ข้อมูลจริงแสดงผล
2. เขียนกลับ `salePrice1..5` + audit log
3. ย้ายราคาราย DOT ขึ้น server (multi-device sync)
4. ผูก `incomingInfo` กับระบบ PO
5. ระบบสิทธิ์ (admin/btire/dealer/counter) คุมการเห็นทุน/แก้ราคา

> เอกสารนี้คู่กับ `app-xls2/README-โครงสร้าง.md` (โครงสร้างไฟล์/โหลด) — อ่านประกอบกัน

---

## 8) โมเดล API รายเส้น + การผูกฟิลด์ของสถานะ (ยืนยันทิศทาง)
- **API รายเส้น (per code13):** ดึงข้อมูลสินค้ารายตัวด้วยรหัส 13 หลัก → เขียนราคากลับ (เฉพาะ salePrice1..5)
- **สถานะพิเศษที่มีลิงก์:** ผูกกับ "ฟิลด์/เงื่อนไขของสินค้า" (เช่น `incoming`, `qtyOnHand`, `flags.*`) โดย**อ้างอิงจากรหัสสินค้า (code13) ที่ผูกในแถวนั้น** — เหมือนคอลัมน์อื่นที่เชื่อม DB
- ตัวบ่งชี้ 🔗 ในหน้า "ตั้งค่า → ไอคอนสถานะ" บอกว่าสถานะนั้นอ่านจากฟิลด์ไหน · เปลี่ยนชื่อ/ไอคอน/สีได้โดยลิงก์ (cond→field) ไม่เปลี่ยน
- **อนาคต:** เปิดให้ผูกสถานะกำหนดเองเข้ากับฟิลด์ DB ใดก็ได้ (custom cond = `field:<key> <op> <value>`) ผ่าน UI โดยตรง
