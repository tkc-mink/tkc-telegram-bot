/* perm-enforce.js — บังคับ "สิทธิ์มองเห็นตามตำแหน่ง" จริงบนตาราง (ทำงานตอน render)
   โหลดหลัง device-registry-client.js + admin-central.js + sheet-grid.js
   ────────────────────────────────────────────────────────────────────────
   เปิด global: window.PermEnforce
     PermEnforce.isEnforced()              → เปิดบังคับบนเครื่องนี้ไหม
     PermEnforce.setEnforce(bool)          → เปิด/ปิดบังคับ (เก็บในเครื่อง · default ปิด)
     PermEnforce.refresh()                 → resolve สิทธิ์ของ user ที่ login ใหม่ + re-render
     PermEnforce.active()                  → true เมื่อ "บังคับอยู่ + มีตำแหน่งที่ resolve แล้ว" (sheet-grid เรียกเช็ค)
     PermEnforce.colHiddenField(fieldKey)  → คอลัมน์ที่ผูกฟิลด์นี้ ควรซ่อนไหม
     PermEnforce.rowHiddenProduct(product) → แถวสินค้านี้ ควรซ่อนไหม
   ────────────────────────────────────────────────────────────────────────
   ปลอดภัยไว้ก่อน: บังคับ (enforce) ปิดเป็นค่าเริ่มต้น → ไม่ซ่อน/ไม่บล็อกใคร จนกว่าแอดมินจะเปิดเอง
   ระบบ "ดูได้เฉพาะ" (allow) ที่ลิสต์ว่าง = ถือว่าไม่จำกัด (กันเผลอซ่อนหมดทั้งจอ)
*/
(function () {
  'use strict';
  var K_ENFORCE = 'xls2_permenforce';
  var cur = null;          // { assigned, cols, rows } ของ user ปัจจุบัน (null = ยังไม่ resolve)
  var curUser = null;
  var resolving = false;

  function ls(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function isEnforced() { return ls(K_ENFORCE, '') === '1'; }
  function setEnforce(b) { try { b ? localStorage.setItem(K_ENFORCE, '1') : localStorage.removeItem(K_ENFORCE); } catch (e) {} if (b) refresh(); else { cur = null; rerender(); } }
  function whoami() {
    try { if (window.DBX && DBX.currentUser && DBX.currentUser()) return DBX.currentUser(); } catch (e) {}
    try { if (window.Auth && Auth.currentUser && Auth.currentUser()) return Auth.currentUser(); } catch (e) {}
    return '';
  }
  function rerender() { try { if (window.SG && SG.render) SG.render(); } catch (e) {} }

  // resolve สิทธิ์ของ user ที่ login → เก็บไว้ใช้ตอน render (cache ออฟไลน์อยู่ใน Registry)
  function refresh() {
    if (!isEnforced()) { cur = null; rerender(); updateBlock(); return Promise.resolve(null); }
    var user = whoami();
    curUser = user;
    if (!user || !window.Registry || !Registry.permResolve) { cur = null; rerender(); updateBlock(); return Promise.resolve(null); }
    resolving = true;
    return Registry.permResolve(user).then(function (res) {
      resolving = false;
      cur = (res && res.ok) ? { assigned: !!res.assigned, cols: res.cols || null, rows: res.rows || null, name: res.name || '' } : null;
      rerender(); updateBlock();
      return cur;
    }).catch(function () {
      resolving = false;
      var c = (window.Registry && Registry.permCached) ? Registry.permCached(user) : null;   // ออฟไลน์ → cache
      cur = (c && c.ok) ? { assigned: !!c.assigned, cols: c.cols || null, rows: c.rows || null, name: c.name || '' } : null;
      rerender(); updateBlock();
      return cur;
    });
  }

  // active = ควรเอากฎซ่อนคอลัมน์/แถวมาใช้ (บังคับอยู่ + ผูกตำแหน่งแล้ว)
  function active() { return isEnforced() && !!cur && cur.assigned === true; }

  // ── คอลัมน์ ──
  function colHiddenField(field) {
    if (!active() || !cur.cols) return false;
    var c = cur.cols, list = c.fields || [];
    if (c.mode === 'allow') { if (!list.length) return false; return list.indexOf(field) < 0; }   // ดูได้เฉพาะที่ติ๊ก
    return list.indexOf(field) >= 0;                                                              // ซ่อนที่ติ๊ก (block)
  }

  // ── แถว ──
  function ruleMatch(rule, p) {
    if (!rule || !p) return false;
    var v = String(rule.value == null ? '' : rule.value).trim();
    if (!v) return false;
    if (rule.type === 'brand') return String(p.brandCode || p.brand || '').trim() === v || String(p.brandName || '').trim() === v;
    if (rule.type === 'group') return String(p.group || '').trim() === v;
    if (rule.type === 'cat') return String(p.category || p.cat || '').trim() === v;
    if (rule.type === 'code') return String(p.code13 || '').trim() === v;
    return false;
  }
  function rowHiddenProduct(p) {
    if (!active() || !cur.rows) return false;
    var r = cur.rows, rules = r.rules || [];
    if (!rules.length) return false;
    var matched = false;
    for (var i = 0; i < rules.length; i++) { if (ruleMatch(rules[i], p)) { matched = true; break; } }
    if (r.mode === 'allow') return !matched;   // ดูได้เฉพาะที่ตรงเงื่อนไข → ไม่ตรง = ซ่อน
    return matched;                            // ซ่อนที่ตรงเงื่อนไข (block)
  }

  // ── จอบล็อก: user login แล้วแต่ยังไม่ผูกตำแหน่ง (บังคับอยู่) ──
  var blockEl = null;
  function updateBlock() {
    var shouldBlock = isEnforced() && !resolving && !!whoami() && !!cur && cur.assigned === false;
    if (shouldBlock) {
      if (!blockEl) {
        blockEl = document.createElement('div'); blockEl.id = 'perm-block';
        blockEl.innerHTML =
          '<div class="pb-box"><div class="pb-ic">🚫</div>' +
          '<div class="pb-ttl">ยังไม่ได้กำหนดตำแหน่ง</div>' +
          '<div class="pb-sub">บัญชี <b>' + esc(whoami()) + '</b> ยังไม่ถูกผูกกับตำแหน่งใด<br>จึงยังไม่มีสิทธิ์มองเห็นข้อมูล — กรุณาแจ้งแอดมินให้กำหนดตำแหน่งให้</div>' +
          '<div class="pb-btns"><button class="pb-admin">🛡️ แอดมินกำหนดตำแหน่ง</button></div></div>';
        injectCss();
        document.body.appendChild(blockEl);
        blockEl.querySelector('.pb-admin').onclick = function () { if (window.AdminCentral) AdminCentral.open(); };
      }
      blockEl.style.display = 'flex';
    } else if (blockEl) { blockEl.style.display = 'none'; }
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function injectCss() {
    if (document.getElementById('perm-css')) return;
    var s = document.createElement('style'); s.id = 'perm-css';
    s.textContent =
      '#perm-block{position:fixed;inset:0;z-index:99000;background:rgba(28,22,16,.93);backdrop-filter:blur(5px);display:flex;align-items:center;justify-content:center;font-family:Arial,Tahoma,sans-serif;}' +
      '#perm-block .pb-box{max-width:360px;text-align:center;color:#fff;padding:30px;}' +
      '#perm-block .pb-ic{font-size:54px;margin-bottom:10px;}' +
      '#perm-block .pb-ttl{font-size:20px;font-weight:800;margin-bottom:8px;}' +
      '#perm-block .pb-sub{font-size:13.5px;line-height:1.7;color:#d6cdc4;margin-bottom:22px;}' +
      '#perm-block .pb-admin{height:44px;padding:0 22px;border:none;border-radius:11px;background:#F47C20;color:#fff;font:800 14px/1 inherit;cursor:pointer;}' +
      '#perm-block .pb-admin:hover{background:#e06f12;}';
    document.head.appendChild(s);
  }

  window.PermEnforce = {
    isEnforced: isEnforced, setEnforce: setEnforce, refresh: refresh, active: active,
    colHiddenField: colHiddenField, rowHiddenProduct: rowHiddenProduct,
    current: function () { return cur; }
  };

  // boot: resolve ตอนเปิดแอป (ถ้าบังคับอยู่) + re-resolve เมื่อกลับมาโฟกัสหน้าต่าง
  function boot() { if (isEnforced()) refresh(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  window.addEventListener('focus', function () { if (isEnforced() && whoami() !== curUser) refresh(); });
})();
