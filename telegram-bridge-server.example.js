/* ============================================================
   ตัวอย่างเซิร์ฟเวอร์สะพาน Telegram ↔ โปรแกรมแก้ราคายาง v2
   รันบนเครื่อง local ของคุณ (Node.js)
   ------------------------------------------------------------
   ติดตั้ง:   npm i ws node-telegram-bot-api
   รัน:       node telegram-bridge-server.example.js
   ตั้งค่า:   แก้ TELEGRAM_TOKEN, READ_TOKEN, ADMIN_TOKEN, ADMIN_CHAT_IDS
   จากนั้นเปิดโปรแกรมแก้ราคายาง → ⋯ → 🔌 Telegram API → ใส่ ws://localhost:8765 → เปิดใช้
   ============================================================ */
const WebSocket = require('ws');
const TelegramBot = require('node-telegram-bot-api');

const TELEGRAM_TOKEN = 'ใส่โทเคนบอทจาก @BotFather';
const READ_TOKEN  = 'READ-XXXXXXXX';   // ให้ตรงกับในโปรแกรม (หน้าต่าง Telegram API)
const ADMIN_TOKEN = 'ADMIN-XXXXXXXX';  // ให้ตรงกับในโปรแกรม
const ADMIN_CHAT_IDS = [123456789];    // chat id ที่อนุญาตให้สั่งงานระดับแอดมิน

// ---- WS hub: โปรแกรมแก้ราคายางจะเชื่อมเข้ามาเป็น "app" ----
const wss = new WebSocket.Server({ port: 8765 });
let app = null;
let pending = {}; let seq = 0;

wss.on('connection', (sock) => {
  sock.on('message', (raw) => {
    let msg; try { msg = JSON.parse(raw); } catch (e) { return; }
    if (msg.role === 'app') { app = sock; console.log('✓ โปรแกรมเชื่อมต่อแล้ว:', msg.name); return; }
    if (msg.id && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; }
  });
  sock.on('close', () => { if (sock === app) { app = null; console.log('✗ โปรแกรมหลุดการเชื่อมต่อ'); } });
});

function call(method, params, token) {
  return new Promise((resolve, reject) => {
    if (!app || app.readyState !== WebSocket.OPEN) return reject('โปรแกรมแก้ราคายางยังไม่ได้เปิด/เชื่อมต่อ');
    const id = 'm' + (++seq);
    pending[id] = (reply) => reply.ok ? resolve(reply.result) : reject(reply.error);
    app.send(JSON.stringify({ id, method, params, token }));
    setTimeout(() => { if (pending[id]) { delete pending[id]; reject('timeout'); } }, 10000);
  });
}

// ---- Telegram bot ----
const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });
const fmt = (n) => n == null || n === '' ? '-' : Number(String(n).replace(/,/g, '')).toLocaleString('en-US');

bot.onText(/^\/ราคา (.+)/, async (m, g) => {
  try {
    const r = await call('price.check', { q: g[1] }, READ_TOKEN);
    if (!r.count) return bot.sendMessage(m.chat.id, 'ไม่พบสินค้า');
    bot.sendMessage(m.chat.id, r.items.map(i =>
      `${i.size} ${i.brand} ${i.model}\nราคาตั้ง ${fmt(i.retail)} · B ${fmt(i.B)} · A ${fmt(i.A)} · S ${fmt(i.S)}${i.pending ? ' ⏳รอปรับ' : ''}`
    ).join('\n\n'));
  } catch (e) { bot.sendMessage(m.chat.id, '⚠️ ' + e); }
});

// /แก้ราคา <ข้อความค้นหา> <ช่อง:retail|B|A|S|cost> <ราคาใหม่>
bot.onText(/^\/แก้ราคา (.+) (retail|B|A|S|cost) (\d+)/, async (m, g) => {
  if (!ADMIN_CHAT_IDS.includes(m.chat.id)) return bot.sendMessage(m.chat.id, '⛔ เฉพาะแอดมิน');
  try {
    const r = await call('admin.price.set', { q: g[1], field: g[2], value: g[3] }, ADMIN_TOKEN);
    bot.sendMessage(m.chat.id, `✏️ แก้แล้ว ${r.updated} รายการ:\n` + r.items.map(i => `${i.size} ${i.model} → ${g[2]} = ${fmt(i.value)}`).join('\n'));
  } catch (e) { bot.sendMessage(m.chat.id, '⚠️ ' + e); }
});

// /เผยแพร่ [2026-06-15 08:00]
bot.onText(/^\/เผยแพร่(?: (.+))?/, async (m, g) => {
  if (!ADMIN_CHAT_IDS.includes(m.chat.id)) return bot.sendMessage(m.chat.id, '⛔ เฉพาะแอดมิน');
  try {
    const r = await call('admin.update.publish', { effectiveAt: g[1] || '' }, ADMIN_TOKEN);
    bot.sendMessage(m.chat.id, `📤 เผยแพร่ราคาแล้ว · มีผล: ${r.effectiveAt}`);
  } catch (e) { bot.sendMessage(m.chat.id, '⚠️ ' + e); }
});

console.log('🚀 สะพาน Telegram พร้อมที่ ws://localhost:8765');
