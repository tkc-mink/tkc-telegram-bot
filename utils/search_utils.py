# search_utils.py
# -*- coding: utf-8 -*-
"""
Stable image search utilities (no API key)
- Google Images (public HTML)
- Bing Images (public HTML/JS meta)
- DuckDuckGo Images (public i.js with vqd)
- Robust fallback order + in-memory cache + retry/backoff

Tunable ENV:
- SEARCH_TIMEOUT_SEC          (default 10)
- SEARCH_RETRIES              (default 2)   # total attempts = 1 + SEARCH_RETRIES
- SEARCH_BACKOFF_BASE_SEC     (default 0.4)
- SEARCH_CACHE_TTL_SEC        (default 60)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import re
import json
import time
import random

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, urlunparse, parse_qsl, urlencode

# ---------- Config ----------
TIMEOUT = float(os.getenv("SEARCH_TIMEOUT_SEC", "10"))
RETRIES = int(os.getenv("SEARCH_RETRIES", "2"))
BACKOFF_BASE = float(os.getenv("SEARCH_BACKOFF_BASE_SEC", "0.4"))
CACHE_TTL = float(os.getenv("SEARCH_CACHE_TTL_SEC", "60"))

# Keep compatibility constant (some callers import UA)
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_UA_POOL = [
    UA,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
]

_session = requests.Session()
_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (ts, value)


# ---------- Helpers ----------
def _log(tag: str, **kw):
    try:
        print(f"[search_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[search_utils] {tag} :: {kw}")


def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {
        "User-Agent": random.choice(_UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }
    if extra:
        h.update(extra)
    return h


def _retry_sleep(attempt: int, retry_after: Optional[float] = None):
    if retry_after is not None:
        try:
            time.sleep(min(float(retry_after), 3.0))
            return
        except Exception:
            pass
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))


def _http_get(url: str, *, params: Optional[Dict[str, Any]] = None, timeout: float = TIMEOUT) -> Optional[requests.Response]:
    last_err = None
    for attempt in range(1, RETRIES + 2):
        try:
            r = _session.get(url, params=params or {}, headers=_headers(), timeout=timeout)
            if r.status_code == 429:
                retry_after = None
                try:
                    j = r.json()
                    retry_after = j.get("parameters", {}).get("retry_after")
                except Exception:
                    pass
                _log("HTTP_429", url=url, attempt=attempt, retry_after=retry_after)
                if attempt <= RETRIES:
                    _retry_sleep(attempt, retry_after)
                    continue
            if r.ok:
                return r
            _log("HTTP_ERROR", url=url, status=r.status_code)
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except requests.RequestException as e:
            last_err = str(e)
            _log("HTTP_EXCEPTION", url=url, attempt=attempt, err=last_err)
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except Exception as e:
            last_err = str(e)
            _log("HTTP_UNKNOWN", url=url, attempt=attempt, err=last_err)
            if attempt <= RETRIES:
                _retry_sleep(attempt)
    _log("HTTP_GIVEUP", url=url, last_err=str(last_err) if last_err else None)
    return None


def _soup(html: str) -> BeautifulSoup:
    # lxml if available; fall back to html.parser quietly
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def _cache_get(key: str):
    if key in _cache:
        ts, val = _cache[key]
        if (time.time() - ts) <= CACHE_TTL:
            return val
        _cache.pop(key, None)
    return None


def _cache_put(key: str, val: Any):
    _cache[key] = (time.time(), val)


def _is_data_url(u: str) -> bool:
    return u.startswith("data:image/")


def _clean_url(u: str) -> str:
    """
    Remove known tracking params; keep image URL intact.
    """
    try:
        p = urlparse(u)
        if not p.scheme.startswith("http"):
            return u
        qs = dict(parse_qsl(p.query, keep_blank_values=True))
        # remove common tracking params
        for k in list(qs.keys()):
            if k.lower() in {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ved", "ei"}:
                qs.pop(k, None)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(qs, doseq=True), p.fragment))
    except Exception:
        return u


def _dedupe_keep_order(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        k = u.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


# ---------- Google Images ----------
def fetch_google_images(query: str, lang_out: str = "th", max_results: int = 3) -> List[str]:
    """ค้นหารูปจาก Google Images (public, no API)"""
    cache_key = f"gimg:{lang_out}:{max_results}:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    headers = _headers()
    # safe=active เพื่อลดภาพไม่เหมาะสม, tbm=isch = images vertical
    url = f"https://www.google.com/search?q={quote(query)}&hl={lang_out}&tbm=isch&safe=active"
    r = _http_get(url)
    if not r or r.status_code != 200:
        _log("GOOGLE_HTTP", status=(r.status_code if r else "N/A"))
        _cache_put(cache_key, [])
        return []

    soup = _soup(r.text)
    imgs: List[str] = []

    # 1) ง่ายสุด: <img src="https..."> (Google เปลี่ยนบ่อย)
    for img in soup.select('img[src^="http"]'):
        src = img.get("src") or ""
        if not src or _is_data_url(src):
            continue
        imgs.append(src)

    # 2) <img data-src="https..."> (บางครั้ง lazy)
    for img in soup.find_all("img"):
        ds = img.get("data-src") or img.get("data-iurl") or ""
        if ds and ds.startswith("http") and not _is_data_url(ds):
            imgs.append(ds)

    # 3) regex เผื่อฝังใน script (AF_initData-like payloads) — เก็บเฉพาะ https และไฟล์รูปที่ดูสมเหตุสมผล
    if len(imgs) < max_results:
        try:
            for m in re.finditer(r'"(https?://[^"]+\.(?:jpg|jpeg|png|gif|webp)[^"]*)"', r.text, flags=re.IGNORECASE):
                url_candidate = m.group(1)
                if not _is_data_url(url_candidate):
                    imgs.append(url_candidate)
        except Exception:
            pass

    # คัดกรองให้เหลือ https เท่านั้น และลบบางโดเมนเงื่อนไขหละหลวม
    filtered = []
    for u in imgs:
        if not u.startswith("http"):
            continue
        if any(bad in u for bad in ["gstatic.com/images?q=tbn", "encrypted-tbn0.gstatic.com/images"]):
            # หมายถึง thumbnail ขนาดเล็กของ Google; ข้ามเพื่อคุณภาพ
            continue
        filtered.append(_clean_url(u))

    results = _dedupe_keep_order(filtered)[:max_results]
    if not results:
        _log("[fetch_google_images] ไม่เจอรูปเลย", query=query)
    _cache_put(cache_key, results)
    return results


# ---------- Bing Images ----------
def fetch_bing_images(query: str, max_results: int = 3) -> List[str]:
    """ค้นหารูปจาก Bing Images (public)"""
    cache_key = f"bing:{max_results}:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://www.bing.com/images/search?q={quote(query)}"
    r = _http_get(url)
    if not r or r.status_code != 200:
        _log("BING_HTTP", status=(r.status_code if r else "N/A"))
        _cache_put(cache_key, [])
        return []

    soup = _soup(r.text)
    image_results: List[str] = []

    # วิธีหลัก: a.iusc มี meta JSON ในแอตทริบิวต์ m
    for a in soup.select("a.iusc"):
        m = a.get("m")
        if not m:
            continue
        try:
            meta = json.loads(m)
            u = meta.get("murl") or meta.get("turl")
            if u and u.startswith("http") and not _is_data_url(u):
                image_results.append(_clean_url(u))
            if len(image_results) >= max_results:
                break
        except Exception as e:
            _log("BING_META_JSON_ERR", err=str(e))

    # เผื่อวิธีเสริม: <img class="mimg" ...> (thumbnail) — ใช้เฉพาะจำเป็น
    if len(image_results) < max_results:
        for img in soup.select("img.mimg"):
            u = img.get("data-src") or img.get("src") or ""
            if u and u.startswith("http") and not _is_data_url(u):
                image_results.append(_clean_url(u))
            if len(image_results) >= max_results:
                break

    results = _dedupe_keep_order(image_results)[:max_results]
    if not results:
        _log("[fetch_bing_images] ไม่เจอรูปเลย", query=query)
    _cache_put(cache_key, results)
    return results


# ---------- DuckDuckGo Images ----------
def _extract_vqd(html: str) -> Optional[str]:
    """
    ดึง vqd token จาก HTML หน้าแรกของ DuckDuckGo
    พบได้ในสคริปต์/อินไลน์หลายรูปแบบ — ใช้ regex หลายแพทเทิร์น
    """
    try:
        # รูปแบบทั่วไป: vqd='3-12345678901234567890123456789012'
        m = re.search(r"vqd=['\"]([0-9-]{5,})['\"]", html)
        if m:
            return m.group(1)
        # แบบอยู่ใน URL
        m = re.search(r"vqd=([0-9-]{5,})\&", html)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def fetch_duckduckgo_images(query: str, max_results: int = 3) -> List[str]:
    """ค้นหารูปจาก DuckDuckGo Images (public)"""
    cache_key = f"ddg:{max_results}:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        session = requests.Session()
        url = f"https://duckduckgo.com/?q={quote(query)}&iar=images&iax=images&ia=images"
        res = session.get(url, headers=_headers(), timeout=TIMEOUT)
        if res.status_code != 200:
            _log("DDG_HTTP", status=res.status_code)
            _cache_put(cache_key, [])
            return []

        vqd = _extract_vqd(res.text)
        if not vqd:
            _log("DDG_NO_VQD")
            _cache_put(cache_key, [])
            return []

        api_url = f"https://duckduckgo.com/i.js?o=json&q={quote(query)}&vqd={vqd}&l=us-en"
        # หมายเหตุ: อาจต้องวนหลายหน้า (s=offset) — ที่นี่เอาหน้าแรกพอ
        api = session.get(api_url, headers=_headers({"Referer": url}), timeout=TIMEOUT)
        if api.status_code != 200:
            _log("DDG_API_HTTP", status=api.status_code)
            _cache_put(cache_key, [])
            return []

        data = api.json()
        results = []
        for it in data.get("results", []):
            u = it.get("image") or it.get("thumbnail")
            if u and u.startswith("http") and not _is_data_url(u):
                results.append(_clean_url(u))
            if len(results) >= max_results:
                break

        results = _dedupe_keep_order(results)[:max_results]
        if not results:
            _log("[fetch_duckduckgo_images] ไม่เจอรูปเลย", query=query)
        _cache_put(cache_key, results)
        return results

    except Exception as e:
        _log("DDG_EXCEPTION", err=str(e))
        _cache_put(cache_key, [])
        return []


# ---------- Robust wrapper ----------
def robust_image_search(query: str, lang_out: str = "th", max_results: int = 3) -> List[str]:
    """
    ค้นหารูปตามลำดับ: Google → Bing → DuckDuckGo
    คืนลิสต์ URL (สูงสุด max_results) หรือ [] ถ้าไม่พบ
    """
    # Cache key รวมทุกพารามิเตอร์
    cache_key = f"robust:{lang_out}:{max_results}:{query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # 1) Google
    results = fetch_google_images(query, lang_out=lang_out, max_results=max_results)
    if results:
        _cache_put(cache_key, results)
        return results

    # 2) Bing
    results = fetch_bing_images(query, max_results=max_results)
    if results:
        _cache_put(cache_key, results)
        return results

    # 3) DuckDuckGo
    results = fetch_duckduckgo_images(query, max_results=max_results)
    if results:
        _cache_put(cache_key, results)
        return results

    _log("ROBUST_EMPTY", query=query)
    _cache_put(cache_key, [])
    return []


# ---------- Optional CLI test ----------
if __name__ == "__main__":
    tests = [
        "แมววิ่งเล่น",
        "mountains wallpaper 4k",
        "tesla cybertruck",
    ]
    for q in tests:
        print("====", q)
        print("Google:", fetch_google_images(q, max_results=3))
        print("Bing  :", fetch_bing_images(q, max_results=3))
        print("DDG   :", fetch_duckduckgo_images(q, max_results=3))
        print("ROBUST:", robust_image_search(q, max_results=3))
        print()
