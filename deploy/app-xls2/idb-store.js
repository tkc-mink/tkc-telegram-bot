/* idb-store.js — IndexedDB wrapper เบาๆ สำหรับเก็บ snapshot ราคา + ดัชนีค้นหาสินค้าในเครื่อง
   โหลดก่อน db-staging.js (db-staging เรียกผ่าน window.IDB) · ถ้าเบราว์เซอร์ไม่รองรับ = degrade เงียบๆ (caller fallback localStorage)
   เปิด global: window.IDB
     IDB.supported()                  → มี IndexedDB ใช้ได้ไหม
     IDB.get(store,key) / set(store,val,key) / del(store,key) / clear(store)   (Promise)
     IDB.count(store) / getAll(store) / bulkPut(store, arr)                    (Promise)
     IDB.searchProducts(q, limit)     → ค้นดัชนีสินค้าในเครื่อง (substring code13/name/brand/size/model)
   stores:
     'kv'        → key/value (เก็บ blob snapshot ที่เข้ารหัสแล้ว — ทะลุลิมิต ~5MB ของ localStorage)
     'products'  → keyPath 'code13' (ดัชนีค้นหา · เก็บเฉพาะข้อมูลระบุสินค้า ไม่มีราคา — data-minimization)
*/
(function () {
  'use strict';
  var DB_NAME = 'tkc_xls2', DB_VER = 1, db = null, openP = null;
  var STORES = { kv: {}, products: { keyPath: 'code13' } };

  function supported() { try { return typeof indexedDB !== 'undefined' && !!indexedDB; } catch (e) { return false; } }

  function open() {
    if (db) return Promise.resolve(db);
    if (openP) return openP;
    if (!supported()) return Promise.reject(new Error('no-indexeddb'));
    openP = new Promise(function (res, rej) {
      var r = indexedDB.open(DB_NAME, DB_VER);
      r.onupgradeneeded = function (e) {
        var d = e.target.result;
        Object.keys(STORES).forEach(function (name) {
          if (!d.objectStoreNames.contains(name)) {
            d.createObjectStore(name, STORES[name].keyPath ? { keyPath: STORES[name].keyPath } : undefined);
          }
        });
      };
      r.onsuccess = function (e) { db = e.target.result; res(db); };
      r.onerror = function () { rej(r.error || new Error('idb-open-fail')); };
    });
    return openP;
  }
  function store(name, mode) { return open().then(function (d) { return d.transaction(name, mode).objectStore(name); }); }
  function reqP(req) { return new Promise(function (res, rej) { req.onsuccess = function () { res(req.result); }; req.onerror = function () { rej(req.error); }; }); }

  var IDB = {
    supported: supported,
    get: function (s, key) { return store(s, 'readonly').then(function (os) { return reqP(os.get(key)); }).catch(function () { return null; }); },
    set: function (s, val, key) { return store(s, 'readwrite').then(function (os) { return reqP(key !== undefined ? os.put(val, key) : os.put(val)); }).catch(function () { return null; }); },
    del: function (s, key) { return store(s, 'readwrite').then(function (os) { return reqP(os.delete(key)); }).catch(function () { return null; }); },
    clear: function (s) { return store(s, 'readwrite').then(function (os) { return reqP(os.clear()); }).catch(function () { return null; }); },
    count: function (s) { return store(s, 'readonly').then(function (os) { return reqP(os.count()); }).catch(function () { return 0; }); },
    getAll: function (s) { return store(s, 'readonly').then(function (os) { return reqP(os.getAll()); }).catch(function () { return []; }); },
    bulkPut: function (s, arr) {
      return open().then(function (d) {
        return new Promise(function (res, rej) {
          var t = d.transaction(s, 'readwrite'), os = t.objectStore(s);
          (arr || []).forEach(function (v) { try { os.put(v); } catch (e) {} });
          t.oncomplete = function () { res(true); };
          t.onerror = function () { rej(t.error); };
        });
      }).catch(function () { return false; });
    },
    searchProducts: function (q, limit) {
      q = String(q || '').trim().toLowerCase(); limit = limit || 50;
      return IDB.getAll('products').then(function (arr) {
        if (!q) return arr.slice(0, limit);
        var out = [];
        for (var i = 0; i < arr.length && out.length < limit; i++) {
          var p = arr[i];
          var hay = ((p.code13 || '') + ' ' + (p.name || '') + ' ' + (p.brandCode || '') + ' ' + (p.size || '') + ' ' + (p.model || '')).toLowerCase();
          if (hay.indexOf(q) >= 0) out.push(p);
        }
        return out;
      });
    }
  };
  window.IDB = IDB;
})();
