/* ============================================================
   device-registry — Cloudflare Worker (ทะเบียนกลางอุปกรณ์ + OTP + log)
   สำหรับแอป "แก้ราคายาง" : คุมว่าเครื่องไหนเข้าใช้ได้ · ออก OTP ครั้งแรก · เก็บ log · แอดมินลบอุปกรณ์
   ------------------------------------------------------------
   วิธีติดตั้ง (ครั้งเดียว):
   1) dash.cloudflare.com → Workers & Pages → Create → Worker → ตั้งชื่อ เช่น "tkc-registry" → Deploy
   2) Settings → Variables → "KV Namespace Bindings" → Add :
        Variable name = REGISTRY   (ต้องชื่อนี้)
        KV namespace  = สร้างใหม่ชื่ออะไรก็ได้ เช่น tkc_registry
   3) Settings → Variables → "Environment Variables" → Add :
        ADMIN_KEY = <ตั้งรหัสลับแอดมินยาวๆ ของคุณเอง>     (ใช้ยืนยันฝั่งแอดมิน)
   4) Edit code → ลบของเดิม → วางไฟล์นี้ → Save and Deploy
   5) คัดลอก URL เช่น  https://tkc-registry.<บัญชี>.workers.dev  ไปตั้งในแอป

   ทุก request เป็น POST  body JSON: { action, ... }  ตอบกลับ JSON เสมอ
   ------------------------------------------------------------
   ACTIONS:
     OTP_REQUEST  {user, deviceId, deviceName, deviceType}  → {ok, ref}      ออกรหัส 6 หลัก (อายุ 3 นาที) + ตั้งคำขอรออนุมัติ
     OTP_VERIFY   {deviceId, code}                          → {ok, token}    ตรวจรหัส → ลงทะเบียนอุปกรณ์ + ออก token
     DEVICE_CHECK {deviceId, token}                         → {ok} / {revoked:true}   เช็กทุกครั้งที่เปิดแอป
     LOG_PUSH     {deviceId, token, event, meta}            → {ok}           บันทึก log เหตุการณ์
   ADMIN (ต้องส่ง adminKey ให้ตรง ADMIN_KEY):
     DEVICE_LIST   {adminKey}                  → {devices:[...], pending:[...]}
     DEVICE_REVOKE {adminKey, deviceId}        → {ok}        ลบ/เพิกถอน → เครื่องนั้นเข้าไม่ได้อีก ต้อง OTP ใหม่
     LOG_LIST      {adminKey, limit}           → {logs:[...]}
     PERM_GET      {adminKey}                  → {positions:[...], userpos:{user:posId}}   อ่านผังสิทธิ์มองเห็นรายตำแหน่ง + การผูกคน
     PERM_SET      {adminKey, positions?, userpos?} → {ok}   บันทึก (ส่งมาส่วนไหนบันทึกส่วนนั้น)
   USER (ไม่ต้อง adminKey):
     PERM_RESOLVE  {user}                      → {assigned, posId, name, cols, rows}   — แอปถามสิทธิ์มองเห็นของ user ที่ login
   ============================================================ */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST,OPTIONS',
  'Access-Control-Allow-Headers': '*',
  'Cache-Control': 'no-store',
};
const json = (o, status = 200) =>
  new Response(JSON.stringify(o), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });

const OTP_TTL = 180;          // วินาที (3 นาที)
const LOG_KEEP = 1000;        // เก็บ log ล่าสุดกี่รายการ
const rnd = (n) => Array.from(crypto.getRandomValues(new Uint8Array(n)))
  .map((b) => ('0' + b.toString(16)).slice(-2)).join('');
const otpCode = () => String(Math.floor(100000 + Math.random() * 900000));   // 6 หลัก

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    if (request.method !== 'POST') return json({ error: 'POST only' }, 405);
    if (!env.REGISTRY) return json({ error: 'ยังไม่ผูก KV (REGISTRY)' }, 500);

    let body;
    try { body = await request.json(); } catch (e) { return json({ error: 'body ต้องเป็น JSON' }, 400); }
    const KV = env.REGISTRY;
    const action = body.action;
    const requireAdmin = () => env.ADMIN_KEY && body.adminKey === env.ADMIN_KEY;

    try {
      switch (action) {
        // ---------- USER: ขอ OTP ครั้งแรก ----------
        case 'OTP_REQUEST': {
          if (!body.deviceId || !body.user) return json({ error: 'ต้องมี user + deviceId' }, 400);
          const code = otpCode();
          const pending = {
            deviceId: body.deviceId, user: body.user,
            deviceName: body.deviceName || '', deviceType: body.deviceType === 'bound' ? 'bound' : 'shared',
            code, ts: Date.now(), exp: Date.now() + OTP_TTL * 1000,
          };
          // เก็บ otp (หมดอายุเอง) + คำขอรออนุมัติ (ให้แอดมินเห็นรหัส)
          await KV.put('otp:' + body.deviceId, JSON.stringify(pending), { expirationTtl: OTP_TTL });
          await KV.put('pending:' + body.deviceId, JSON.stringify(pending), { expirationTtl: OTP_TTL });
          return json({ ok: true, ref: body.deviceId, expiresIn: OTP_TTL });
          // หมายเหตุ: รหัสจะไปโผล่ใน DEVICE_LIST (pending) ให้แอดมินอ่าน/บอกผู้ใช้
        }

        // ---------- USER: ยืนยัน OTP → ลงทะเบียนอุปกรณ์ ----------
        case 'OTP_VERIFY': {
          const raw = await KV.get('otp:' + body.deviceId);
          if (!raw) return json({ error: 'รหัสหมดอายุหรือไม่พบคำขอ' }, 400);
          const p = JSON.parse(raw);
          if (String(body.code) !== String(p.code)) return json({ error: 'รหัสไม่ถูกต้อง' }, 401);
          if (Date.now() > p.exp) return json({ error: 'รหัสหมดอายุ' }, 401);
          const token = rnd(24);
          const dev = {
            deviceId: p.deviceId, user: p.user, name: p.deviceName, type: p.deviceType,
            status: 'active', token, firstSeen: Date.now(), lastSeen: Date.now(),
          };
          await KV.put('dev:' + p.deviceId, JSON.stringify(dev));
          await KV.delete('otp:' + p.deviceId);
          await KV.delete('pending:' + p.deviceId);
          await pushLog(KV, { deviceId: p.deviceId, user: p.user, event: 'register', name: p.deviceName });
          return json({ ok: true, token, user: p.user, type: p.deviceType });
        }

        // ---------- USER: เช็กว่าอุปกรณ์ยังใช้ได้ (เรียกทุกครั้งที่เปิดแอป) ----------
        case 'DEVICE_CHECK': {
          const raw = await KV.get('dev:' + body.deviceId);
          if (!raw) return json({ revoked: true, reason: 'ไม่พบอุปกรณ์ (อาจถูกลบ)' });
          const dev = JSON.parse(raw);
          if (dev.status !== 'active' || dev.token !== body.token) return json({ revoked: true });
          dev.lastSeen = Date.now();
          await KV.put('dev:' + body.deviceId, JSON.stringify(dev));
          return json({ ok: true, user: dev.user, type: dev.type, name: dev.name });
        }

        // ---------- USER: ส่ง log ----------
        case 'LOG_PUSH': {
          const raw = await KV.get('dev:' + body.deviceId);
          if (!raw) return json({ revoked: true });
          const dev = JSON.parse(raw);
          if (dev.token !== body.token) return json({ error: 'token ไม่ถูก' }, 401);
          await pushLog(KV, { deviceId: body.deviceId, user: dev.user, event: body.event || '', meta: body.meta || null });
          return json({ ok: true });
        }

        // ---------- ADMIN: รายการอุปกรณ์ + คำขอรออนุมัติ ----------
        case 'DEVICE_LIST': {
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          const devices = [], pending = [];
          let cursor;
          do {
            const list = await KV.list({ prefix: 'dev:', cursor });
            for (const k of list.keys) { const v = await KV.get(k.name); if (v) { const d = JSON.parse(v); delete d.token; devices.push(d); } }
            cursor = list.cursor; if (list.list_complete) cursor = null;
          } while (cursor);
          const pl = await KV.list({ prefix: 'pending:' });
          for (const k of pl.keys) { const v = await KV.get(k.name); if (v) pending.push(JSON.parse(v)); }
          return json({ ok: true, devices, pending });
        }

        // ---------- ADMIN: ลบ/เพิกถอนอุปกรณ์ ----------
        case 'DEVICE_REVOKE': {
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          const raw = await KV.get('dev:' + body.deviceId);
          await KV.delete('dev:' + body.deviceId);
          if (raw) { const d = JSON.parse(raw); await pushLog(KV, { deviceId: body.deviceId, user: d.user, event: 'revoke', name: d.name }); }
          return json({ ok: true });
        }

        // ---------- ADMIN: ดู log ----------
        case 'LOG_LIST': {
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          const lim = Math.min(body.limit || 200, LOG_KEEP);
          const list = await KV.list({ prefix: 'log:' });
          const keys = list.keys.map((k) => k.name).sort().reverse().slice(0, lim);
          const logs = [];
          for (const name of keys) { const v = await KV.get(name); if (v) logs.push(JSON.parse(v)); }
          return json({ ok: true, logs });
        }

        // ---------- ADMIN: ดึง/บันทึก ตำแหน่ง + การผูก user→ตำแหน่ง (สิทธิ์มองเห็นแถว/คอลัม) ----------
        case 'PERM_GET': {
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          const positions = JSON.parse((await KV.get('perm:positions')) || '[]');
          const userpos = JSON.parse((await KV.get('perm:userpos')) || '{}');
          return json({ ok: true, positions, userpos });
        }

        case 'PERM_SET': {
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          if (body.positions !== undefined) {
            if (!Array.isArray(body.positions)) return json({ error: 'positions ต้องเป็น array' }, 400);
            await KV.put('perm:positions', JSON.stringify(body.positions));
          }
          if (body.userpos !== undefined) {
            if (typeof body.userpos !== 'object' || body.userpos === null) return json({ error: 'userpos ต้องเป็น object' }, 400);
            await KV.put('perm:userpos', JSON.stringify(body.userpos));
          }
          await pushLog(KV, { deviceId: body.deviceId || '', user: body.by || 'admin', event: 'perm_set' });
          return json({ ok: true });
        }

        // ---------- USER: แอปถามสิทธิ์มองเห็นของ user ที่ login (ไม่ต้อง adminKey — ไม่ใช่ข้อมูลราคา) ----------
        case 'PERM_RESOLVE': {
          const u = String(body.user || '').trim();
          if (!u) return json({ error: 'ต้องมี user' }, 400);
          const userpos = JSON.parse((await KV.get('perm:userpos')) || '{}');
          const posId = userpos[u];
          if (!posId) return json({ ok: true, assigned: false });
          const positions = JSON.parse((await KV.get('perm:positions')) || '[]');
          const pos = positions.find((p) => p.id === posId);
          if (!pos) return json({ ok: true, assigned: false });
          return json({ ok: true, assigned: true, posId: pos.id, name: pos.name, cols: pos.cols || null, rows: pos.rows || null });
        }

        // ---------- ข้อมูลขนาด/ชนิดสินค้า (ความสูง/กว้าง/ชนิด/alias) — เก็บกลาง แชร์ทุกเครื่อง ----------
        case 'PRODINFO_GET': {           // USER: ดึงตารางข้อมูลสินค้า (ไม่ใช่ราคา — ไม่ต้อง adminKey)
          const data = JSON.parse((await KV.get('prodinfo')) || '{}');
          return json({ ok: true, data });
        }
        case 'PRODINFO_SET': {           // ADMIN: บันทึกตารางทั้งก้อน
          if (!requireAdmin()) return json({ error: 'adminKey ไม่ถูกต้อง' }, 403);
          if (typeof body.data !== 'object' || body.data === null) return json({ error: 'data ต้องเป็น object' }, 400);
          await KV.put('prodinfo', JSON.stringify(body.data));
          await pushLog(KV, { deviceId: body.deviceId || '', user: body.by || 'admin', event: 'prodinfo_set' });
          return json({ ok: true });
        }

        default:
          return json({ error: 'action ไม่รู้จัก: ' + action }, 400);
      }
    } catch (e) {
      return json({ error: 'server error: ' + (e && e.message || e) }, 500);
    }
  },
};

// เก็บ log (key เรียงตามเวลา → sort ได้) + เก็บแค่ LOG_KEEP ล่าสุด
async function pushLog(KV, entry) {
  const ts = Date.now();
  const key = 'log:' + ts + ':' + Math.random().toString(36).slice(2, 7);
  await KV.put(key, JSON.stringify({ ...entry, ts }));
  // ตัด log เก่าทิ้งถ้าเกินจำนวน (เป็นครั้งคราว)
  if (Math.random() < 0.05) {
    const list = await KV.list({ prefix: 'log:' });
    if (list.keys.length > LOG_KEEP) {
      const old = list.keys.map((k) => k.name).sort().slice(0, list.keys.length - LOG_KEEP);
      for (const name of old) await KV.delete(name);
    }
  }
}
