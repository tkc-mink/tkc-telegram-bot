/* ============================================================
   ddg-image-proxy — Cloudflare Worker
   พร็อกซีค้นรูป DuckDuckGo ให้แอป "แก้ราคายาง" เรียกได้ตรงๆ ไม่ติด CORS
   ------------------------------------------------------------
   วิธีติดตั้ง (ครั้งเดียว):
   1) เข้า dash.cloudflare.com → Workers & Pages → Create → Worker
   2) ตั้งชื่อ เช่น "ddg-img" → Deploy → Edit code
   3) ลบโค้ดเดิมทั้งหมด แล้ววางไฟล์นี้ → Save and Deploy
   4) คัดลอก URL ที่ได้ เช่น  https://ddg-img.<ชื่อบัญชี>.workers.dev
   5) ในแอป: เปิดหน้าต่าง "ค้นหารูปภาพ" → กดลิงก์ "⚙ ตั้งค่าพร็อกซี" → วาง URL → เสร็จ

   โหมดการใช้งาน (แอปเรียกให้อัตโนมัติ):
     ?q=KEYWORD        → ค้นรูป คืน JSON { results:[{thumb,url,title,w,h}] }
     ?url=ENCODED_URL  → ดึงไฟล์รูปผ่านพร็อกซี (ใช้ตอน "นำเข้า" รูปที่โดน CORS บล็อก)
   ============================================================ */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET,OPTIONS',
  'Access-Control-Allow-Headers': '*',
  'Cache-Control': 'no-store',
};

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36';

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });

    const u = new URL(request.url);
    const q = u.searchParams.get('q');
    const passthru = u.searchParams.get('url');

    // โหมด 2: ดึงไฟล์รูปผ่านพร็อกซี (ตอนนำเข้ารูป)
    if (passthru) {
      try {
        const r = await fetch(passthru, {
          headers: { 'User-Agent': UA, 'Referer': 'https://duckduckgo.com/' },
          cf: { cacheTtl: 300 },
        });
        const buf = await r.arrayBuffer();
        const h = new Headers(CORS);
        h.set('Content-Type', r.headers.get('Content-Type') || 'application/octet-stream');
        return new Response(buf, { status: r.status, headers: h });
      } catch (e) {
        return json({ error: 'fetch-failed: ' + e }, 502);
      }
    }

    // โหมด 1: ค้นรูป
    if (q) {
      try {
        const results = await ddgImages(q);
        return json({ q, count: results.length, results });
      } catch (e) {
        return json({ error: String(e && e.message || e), results: [] }, 502);
      }
    }

    return json({ ok: true, usage: '?q=KEYWORD  หรือ  ?url=ENCODED_URL' });
  },
};

function json(obj, status = 200) {
  const h = new Headers(CORS);
  h.set('Content-Type', 'application/json; charset=utf-8');
  return new Response(JSON.stringify(obj), { status, headers: h });
}

// ---- หา vqd token จากหน้า DuckDuckGo ----
async function getVqd(q) {
  const r = await fetch(
    'https://duckduckgo.com/?q=' + encodeURIComponent(q) + '&iar=images&iax=images&ia=images',
    { headers: { 'User-Agent': UA, 'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9' } }
  );
  const t = await r.text();
  // รองรับหลายรูปแบบ: vqd="4-123…"  /  vqd=4-123…&  /  vqd:'4-123…'
  const m =
    t.match(/vqd=["']([\d-]+)["']/) ||
    t.match(/vqd=([\d-]+)&/) ||
    t.match(/vqd=["']([\w.-]+)["']/) ||
    t.match(/vqd[=:]\s*["']?([\w.-]+)/);
  if (!m) throw new Error('vqd-not-found');
  return m[1];
}

// ---- เรียก i.js เอาผลลัพธ์รูป ----
async function ddgImages(q) {
  const vqd = await getVqd(q);
  const r = await fetch(
    'https://duckduckgo.com/i.js?l=us-en&o=json&q=' + encodeURIComponent(q) +
      '&vqd=' + encodeURIComponent(vqd) + '&f=,,,&p=1',
    {
      headers: {
        'User-Agent': UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://duckduckgo.com/',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Language': 'en-US,en;q=0.9',
      },
    }
  );
  const j = await r.json();
  return (j.results || []).map(function (x) {
    return {
      thumb: x.thumbnail || x.image,
      url: x.image || x.thumbnail,
      title: x.title || '',
      w: x.width || 0,
      h: x.height || 0,
    };
  }).filter(function (x) { return x.url; });
}
