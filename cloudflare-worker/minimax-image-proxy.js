/* ============================================================
   minimax-image-proxy — Cloudflare Worker
   ตัวกลางเชื่อม "AI ตกแต่งรูป" ในแอป → MiniMax image-01 (image-to-image)
   ------------------------------------------------------------
   ทำไมต้องมี: เรียก MiniMax ตรงจากเบราว์เซอร์ไม่ได้ (CORS + ต้องซ่อน API key)
   Worker นี้รับ contract ของแอป แล้วไปคุยกับ MiniMax ให้ พร้อมแนบ CORS

   ── ติดตั้ง (ครั้งเดียว) ──
   1) dash.cloudflare.com → Workers & Pages → Create → Worker → ตั้งชื่อ เช่น "minimax-img"
   2) Deploy → Edit code → ลบโค้ดเดิม วางไฟล์นี้ → Save and Deploy
   3) ตั้งค่า API key เป็น "ความลับ" (ปลอดภัยกว่าใส่ในโค้ด):
        Worker → Settings → Variables and Secrets → + Add → ชนิด Secret
        ชื่อ:  MINIMAX_API_KEY      ค่า: <คีย์ MiniMax ของคุณ>
        (ออปชัน) เพิ่ม MINIMAX_HOST = https://api.minimax.io   (หรือ https://api.minimaxi.com สำหรับโซน CN)
   4) คัดลอก URL ของ Worker → ในแอปไปที่ "ตั้งค่า AI" → ช่อง "เว็บภายนอก (API)" → วาง URL → เปิดใช้งาน

   ── Contract ──
   Request : POST JSON { task:"edit"|"removebg", prompt:"...", image:"data:image/...;base64,..." }
   Response: JSON { image:"data:image/...;base64,..." }  หรือ { error:"..." }
   หมายเหตุ: task=removebg จะถูกปฏิเสธ (ตอบ error) เพื่อให้แอปสลับไปใช้
            "เบราว์เซอร์ ลบพื้นหลัง" ที่ตัดพื้นใสได้จริง (image-01 สร้างภาพใหม่ ไม่ได้ alpha)
   ============================================================ */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization',
  'Cache-Control': 'no-store',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
    if (request.method !== 'POST') return json({ error: 'ใช้ POST เท่านั้น' }, 405);

    let body;
    try { body = await request.json(); } catch (e) { return json({ error: 'JSON ไม่ถูกต้อง' }, 400); }

    const task = body.task || 'edit';
    const prompt = (body.prompt || '').trim();
    const image = body.image || '';

    // ลบพื้นหลัง → ให้แอปไปใช้ตัวในเบราว์เซอร์แทน (image-01 ทำพื้นใสจริงไม่ได้)
    if (task === 'removebg') {
      return json({ error: 'image-01 ไม่รองรับพื้นใส — ใช้ตัวลบพื้นหลังในเบราว์เซอร์' }, 422);
    }
    if (!image) return json({ error: 'ไม่มีรูปต้นฉบับ (image)' }, 400);
    if (!prompt) return json({ error: 'ไม่มีคำสั่ง (prompt)' }, 400);

    // คีย์: จาก Secret ของ Worker ก่อน · เผื่อส่งมาทาง header ก็รับได้
    const key = (env && env.MINIMAX_API_KEY) ||
      (request.headers.get('Authorization') || '').replace(/^Bearer\s+/i, '').trim();
    if (!key) return json({ error: 'ยังไม่ได้ตั้งค่า MINIMAX_API_KEY ใน Worker' }, 500);

    const host = (env && env.MINIMAX_HOST) || 'https://api.minimax.io';

    const payload = {
      model: 'image-01',
      prompt: prompt,                       // คำสั่งแก้รูป เช่น "เปลี่ยนพื้นหลังเป็นสีขาว"
      response_format: 'base64',
      n: 1,
      // image-to-image: ใช้รูปเดิมเป็น subject reference (รับ data URI ได้)
      subject_reference: [{ type: 'character', image_file: image }],
    };
    if (body.aspect_ratio) payload.aspect_ratio = body.aspect_ratio;

    let resp, data;
    try {
      resp = await fetch(host + '/v1/image_generation', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      data = await resp.json();
    } catch (e) {
      return json({ error: 'เรียก MiniMax ไม่สำเร็จ: ' + e }, 502);
    }

    // ตรวจสถานะของ MiniMax
    const br = data && data.base_resp;
    if (br && br.status_code && br.status_code !== 0) {
      return json({ error: 'MiniMax: ' + (br.status_msg || ('code ' + br.status_code)) }, 502);
    }
    const arr = data && data.data && (data.data.image_base64 || data.data.images);
    const b64 = Array.isArray(arr) ? arr[0] : arr;
    if (!b64) return json({ error: 'MiniMax ไม่ส่งรูปกลับมา' }, 502);

    // ถ้าเป็น base64 ล้วน เติมหัว data URI ให้แอป
    const out = /^data:image\//.test(b64) ? b64 : ('data:image/jpeg;base64,' + b64);
    return json({ image: out });
  },
};

function json(obj, status = 200) {
  const h = new Headers(CORS);
  h.set('Content-Type', 'application/json; charset=utf-8');
  return new Response(JSON.stringify(obj), { status, headers: h });
}
