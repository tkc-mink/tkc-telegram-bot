/* ============================================================
   sw.js — Service Worker (network-first) สำหรับ DPC-TKC
   เป้าหมาย: เปิดเว็บแล้วได้ "ไฟล์ล่าสุดเสมอ" โดยไม่ต้องกด Ctrl+Shift+R
   วิธีทำงาน:
     • ออนไลน์  → ดึงจากเน็ตก่อนเสมอ (ได้ของใหม่ล่าสุด) แล้วเก็บสำเนาไว้
     • ออฟไลน์  → ใช้สำเนาที่เก็บไว้ (เปิดโปรแกรมได้แม้เน็ตหลุด)
     • จัดการเฉพาะไฟล์ของเราเอง (same-origin GET) — ไม่ยุ่งกับ Google API
   ============================================================ */
var CACHE = 'dpc-tkc-cache-v2';

// ไฟล์แกนหลัก (app shell) — เก็บล่วงหน้าตอนติดตั้ง เพื่อให้เปิดออฟไลน์ได้แม้ยังไม่เคยเข้าหน้านั้น
var SHELL = [
  './', './index.html', './manifest.json',
  './icons/icon-192.png', './icons/icon-512.png', './icons/icon-180.png',
  './app-xls2/css-01-base-grid.css', './app-xls2/css-02-windows.css', './app-xls2/css-03-pickers-dialogs.css',
  './app-xls2/css-04-toolbar-misc.css', './app-xls2/css-05-darkmode-images.css', './app-xls2/css-06-refinements.css'
];

self.addEventListener('install', function (e) {
  self.skipWaiting();
  // เก็บ shell แบบไม่ล้ม install ถ้าบางไฟล์โหลดไม่ได้ (allSettled)
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.allSettled(SHELL.map(function (u) { return c.add(u); }));
  }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { if (k !== CACHE) return caches.delete(k); }));  // ลบ cache เวอร์ชันเก่า
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  // จัดการเฉพาะไฟล์โดเมนเดียวกัน (ของเรา) — ปล่อย Google APIs/อื่นๆ ผ่านไปตามปกติ
  var url;
  try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    fetch(req).then(function (resp) {
      if (resp && resp.ok && resp.type === 'basic') {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
      }
      return resp;
    }).catch(function () {
      return caches.match(req).then(function (hit) { return hit || Promise.reject('offline'); });
    })
  );
});
