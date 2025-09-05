# utils/news_utils.py
# -*- coding: utf-8 -*-
"""
Utility ดึง "ข่าวล่าสุด" ที่เสถียรที่สุดเท่าที่ทำได้ (ไม่มี API key ก็ใช้ได้)
ลำดับความพยายาม:
1) internal_tools.google_search (ถ้ามี) — โครงสร้างเดิมที่คุณใช้อยู่
2) Google News RSS (public, ไม่มี key) — ทั้งหน้าแรกหรือค้นหาตามหัวข้อ
3) Mock (ออฟไลน์/มีปัญหาเครือข่าย) — แสดงผลตัวอย่างเพื่อให้ระบบไม่ล่ม

คุณสมบัติ:
- HTTP retry + backoff
- Timeout กำหนดได้ผ่าน ENV
- แคชชั่วคราวในหน่วยความจำ (TTL)
- ปรับแต่งภาษา/ประเทศได้ (ค่าเริ่มต้นไทย)
- คืนข้อความ Markdown พร้อมลิงก์ (ปลอดภัยต่อ Markdown)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import re
import html
import requests
from urllib.parse import quote
from xml.etree import ElementTree as ET

# =======================
# Tunables / ENV
# =======================
TIMEOUT = float(os.getenv("NEWS_TIMEOUT_SEC", "10"))
RETRIES = int(os.getenv("NEWS_RETRIES", "2"))
BACKOFF_BASE = float(os.getenv("NEWS_BACKOFF_BASE_SEC", "0.4"))
CACHE_TTL = float(os.getenv("NEWS_CACHE_TTL_SEC", "300"))

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# =======================
# Internal search (optional)
# =======================
# โครงสร้างเข้ากันได้กับของเดิม: internal_tools.google_search.search(queries=[...], search_type='NEWS')
_internal_search = None
try:
    from internal_tools import google_search  # type: ignore
    _internal_search = google_search
except Exception:
    _internal_search = None  # จะ fallback เป็น RSS

# =======================
# In-memory cache (TTL)
# =======================
_cache: Dict[str, Tuple[float, Any]] = {}

def _cache_get(key: str):
    v = _cache.get(key)
    if not v:
        return None
    ts, val = v
    if time.time() - ts <= CACHE_TTL:
        return val
    _cache.pop(key, None)
    return None

def _cache_put(key: str, val: Any):
    _cache[key] = (time.time(), val)

# =======================
# HTTP helpers
# =======================
_session = requests.Session()
_session.headers.update({"User-Agent": UA})

def _retry_sleep(attempt: int):
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _http_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
    last_err = None
    for attempt in range(1, RETRIES + 2):
        try:
            r = _session.get(url, params=params or {}, timeout=TIMEOUT)
            if r.ok:
                return r
            last_err = f"HTTP {r.status_code}"
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except requests.RequestException as e:
            last_err = str(e)
            if attempt <= RETRIES:
                _retry_sleep(attempt)
    print(f"[news_utils] _http_get give up: {url} ({last_err})")
    return None

# =======================
# Markdown helpers
# =======================
_MD_CODE = re.compile(r"([`*_~\[\](){}#+\-.!|>])")

def _md_escape(s: str) -> str:
    """หนีอักขระ Markdown พื้นฐาน เพื่อป้องกันข้อความแตกฟอร์แมต"""
    s = s or ""
    return _MD_CODE.sub(r"\\\1", s)

def _clean_text(s: str, max_len: int = 180) -> str:
    s = html.unescape(s or "")
    # ลบแท็ก HTML ง่าย ๆ
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s

# =======================
# Google News RSS
# =======================
def _google_news_rss_url(topic: Optional[str], lang: str, region: str) -> str:
    """
    topic=None หรือ 'ข่าวล่าสุด' -> หน้าแรกประเทศ/ภาษา
    กรณีค้นหา: ใช้ /rss/search?q=...
    """
    ceid = f"{region}:{lang}"
    if not topic or topic.strip() in {"ข่าวล่าสุด", "latest", "headlines"}:
        return f"https://news.google.com/rss?hl={lang}&gl={region}&ceid={ceid}"
    q = quote(topic)
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={region}&ceid={ceid}"

def _parse_google_news_rss(xml_text: str, limit: int = 3) -> List[Dict[str, str]]:
    # โครงสร้าง RSS: <item><title>, <link>, <pubDate>, <source>, <description>
    items: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
        for it in root.findall(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            source_el = it.find("{http://www.w3.org/2005/Atom}source") or it.find("source")
            source = (source_el.text or "").strip() if source_el is not None else ""
            desc = (it.findtext("description") or "").strip()
            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "snippet": _clean_text(desc),
                    "source": source or "Google News",
                })
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"[news_utils] RSS parse error: {e}")
    return items

def _fetch_google_news(topic: Optional[str], lang: str, region: str, limit: int) -> List[Dict[str, str]]:
    url = _google_news_rss_url(topic, lang, region)
    cache_key = f"gn:{lang}:{region}:{topic or 'headlines'}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    resp = _http_get(url)
    if not resp:
        return []
    articles = _parse_google_news_rss(resp.text, limit=limit)
    _cache_put(cache_key, articles)
    return articles

# =======================
# Internal search wrapper
# =======================
def _fetch_internal(topic: str, limit: int) -> List[Dict[str, str]]:
    if not _internal_search:
        return []
    try:
        results = _internal_search.search(queries=[topic], search_type="NEWS")  # type: ignore
        # โครงสร้างคาดหวัง: results[0].results -> list ของ object มี title/link/snippet/source
        if not results or not getattr(results[0], "results", None):
            return []
        out: List[Dict[str, str]] = []
        for item in results[0].results[:limit]:
            out.append({
                "title": str(getattr(item, "title", "")),
                "link": str(getattr(item, "link", "")),
                "snippet": str(getattr(item, "snippet", "")),
                "source": str(getattr(item, "source", "")),
            })
        return out
    except Exception as e:
        print(f"[news_utils] internal search failed: {e}")
        return []

# =======================
# Public API
# =======================
def get_news(
    topic: str = "ข่าวล่าสุด",
    *,
    lang: str = "th",
    region: str = "TH",
    max_items: int = 3,
) -> str:
    """
    ดึงข่าวหัวข้อที่ต้องการ (หรือพาดหัวล่าสุดถ้า topic='ข่าวล่าสุด')
    คืนสตริง Markdown พร้อมลิงก์

    ตัวอย่าง:
        get_news()                  -> พาดหัวข่าวไทยล่าสุด
        get_news("เศรษฐกิจไทย")     -> ค้นหาข่าวเศรษฐกิจไทย
        get_news("AI", lang="en", region="US", max_items=5)
    """
    topic = (topic or "").strip()
    print(f"[news_utils] Fetching news: topic='{topic}', lang={lang}, region={region}, max={max_items}")

    # 1) internal search ก่อน (ถ้ามี)
    articles = _fetch_internal(topic, max_items)
    # 2) fallback → Google News RSS
    if not articles:
        articles = _fetch_google_news(topic, lang=lang, region=region, limit=max_items)

    # 3) mock offline ถ้ายังว่าง
    if not articles:
        articles = [
            {
                "title": "ตัวอย่างข่าว: ระบบออฟไลน์",
                "link": "https://example.com/1",
                "snippet": "นี่คือข้อความสรุปสั้น ๆ เมื่อไม่สามารถเชื่อมต่อเครือข่ายได้",
                "source": "Offline",
            },
            {
                "title": "ตัวอย่างข่าว 2",
                "link": "https://example.com/2",
                "snippet": "ใช้เพื่อให้บอทยังตอบได้และไม่ล่ม",
                "source": "Offline",
            },
        ][:max_items]

    # จัดข้อความ Markdown
    header = f"🗞️ **ข่าวเด่น**" if topic in {"ข่าวล่าสุด", "", None} else f"🗞️ **ข่าวเด่นในหัวข้อ: {_md_escape(topic)}**"
    parts: List[str] = [header]

    for a in articles[:max_items]:
        title = _md_escape(a.get("title", "").strip() or "-")
        link = a.get("link", "").strip() or "#"
        source = _md_escape(a.get("source", "").strip() or "")
        snippet = _md_escape(_clean_text(a.get("snippet", "") or "", max_len=180))

        parts.append(
            f"• **{title}**\n"
            + (f"  _{source}_\n" if source else "")
            + (f"  {snippet}\n" if snippet else "")
            + f"  🔗 [{_md_escape('อ่านต่อ')}]({link})"
        )

    return "\n\n".join(parts)
