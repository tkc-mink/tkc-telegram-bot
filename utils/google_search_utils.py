# utils/google_search_utils.py
# -*- coding: utf-8 -*-

import os
import html
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
try:
    # urllib3 <2 / =2 name shim
    from urllib3.util.retry import Retry  # type: ignore
except Exception:  # pragma: no cover
    Retry = None  # graceful fallback


def _build_session(timeout: int = 10, retries: int = 2, backoff: float = 0.5) -> requests.Session:
    """
    Build a requests session with sane retry defaults for Google CSE.
    """
    s = requests.Session()
    if Retry is not None:
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
    s.request = _wrap_timeout(s.request, timeout)
    return s


def _wrap_timeout(fn, timeout: int):
    def _inner(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return fn(method, url, **kwargs)
    return _inner


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if (v is not None and str(v).strip() != "") else default


def _escape_for_telegram(text: str) -> str:
    """
    Escape for Telegram parse_mode='HTML'
    """
    return html.escape(text, quote=False)


def google_search(
    query: str,
    num: int = 3,
    search_type: str = "web",
    *,
    page: int = 1,
    site: Optional[str] = None,
    lang: Optional[str] = None,     # e.g. 'lang_th' (CSE lr param)
    country: Optional[str] = None,  # e.g. 'th' (CSE gl param)
    safe: Optional[str] = None,     # 'active' | 'off'
    return_format: str = "text",    # 'text' (drop-in default) | 'list'
    timeout: Optional[int] = None,
    img_size: Optional[str] = None, # 'large','xlarge','huge', etc.
    img_type: Optional[str] = None, # 'clipart','photo','face', etc.
) -> Union[str, List[str], List[Dict[str, Any]]]:
    """
    ค้นหาข้อมูลหรือภาพจาก Google Custom Search API

    Drop-in compatibility:
      - search_type='web' -> (default) คืน string ข้อความสรุป (เดิม)
      - search_type='image' -> คืน list[str] ของ image URLs (เดิม)

    Power options (ไม่บังคับ):
      - page: แบ่งหน้า (1-based)
      - site: จำกัดผลภายในโดเมน (siteSearch)
      - lang/country/safe: ควบคุมภาษา/ประเทศ/safe search
      - return_format='list' -> คืน list ของ dict (title/snippet/link) แทน string
    """
    API_KEY = _env("GOOGLE_CSE_API_KEY")
    CSE_ID  = _env("GOOGLE_CSE_ID")
    if not API_KEY or not CSE_ID:
        return "❌ ยังไม่ได้ตั้งค่า GOOGLE_CSE_API_KEY หรือ GOOGLE_CSE_ID"

    # Bounds per CSE: num 1..10 ; start 1..( ~100 )
    try:
        num = max(1, min(10, int(num)))
    except Exception:
        num = 3
    try:
        page = max(1, int(page))
    except Exception:
        page = 1
    start = 1 + (page - 1) * num

    # Defaults from ENV (can be overridden by arguments)
    if lang is None:
        lang = _env("GOOGLE_CSE_LR")          # e.g. 'lang_th'
    if country is None:
        country = _env("GOOGLE_CSE_GL")       # e.g. 'th'
    if safe is None:
        safe = _env("GOOGLE_CSE_SAFE", "off") # 'active' or 'off'
    if timeout is None:
        timeout = int(_env("GOOGLE_CSE_TIMEOUT", "10") or 10)

    params: Dict[str, Any] = {
        "key": API_KEY,
        "cx":  CSE_ID,
        "q":   query,
        "num": num,
        "start": start,
        "safe": safe,
    }
    if site:
        params["siteSearch"] = site
    if country:
        params["gl"] = country
    if lang:
        params["lr"] = lang

    if search_type == "image":
        params["searchType"] = "image"
        if img_size:
            params["imgSize"] = img_size
        if img_type:
            params["imgType"] = img_type

    try:
        session = _build_session(timeout=timeout)
        resp = session.get("https://www.googleapis.com/customsearch/v1", params=params)
        if resp.status_code != 200:
            # Attempt to read API error payload for better diagnostics
            try:
                err = resp.json()
                if isinstance(err, dict) and "error" in err and "message" in err["error"]:
                    return f"❌ เกิดข้อผิดพลาด Google Search: {resp.status_code} — {err['error']['message']}"
            except Exception:
                pass
            return f"❌ เกิดข้อผิดพลาด Google Search: {resp.status_code}"

        data = resp.json()
        # Handle API-level errors in 200 responses
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            msg = err.get("message", "unknown error")
            return f"❌ เกิดข้อผิดพลาด Google Search: {msg}"

        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            return "ไม่พบผลลัพธ์ที่เกี่ยวข้อง"

        if search_type == "image":
            # Return direct image links
            links: List[str] = []
            for item in items[:num]:
                link = item.get("link")
                if link and link not in links:
                    links.append(link)
            return links

        # WEB results
        results_list: List[Dict[str, str]] = []
        for item in items[:num]:
            title = item.get("title") or ""
            snippet = item.get("snippet") or ""
            link = item.get("link") or ""
            results_list.append({
                "title": title,
                "snippet": snippet,
                "link": link,
            })

        if return_format == "list":
            return results_list

        # Default: pretty HTML-ish text (safe for Telegram HTML)
        parts: List[str] = []
        for r in results_list:
            t = _escape_for_telegram(r["title"])
            s = _escape_for_telegram(r["snippet"])
            l = r["link"]  # URL ปล่อยตรง ๆ
            parts.append(f"🔎 <b>{t}</b>\n{s}\n{l}")
        return "\n\n".join(parts)

    except Exception as e:
        print(f"[google_search] {e}")
        return "❌ ดึงข้อมูล Google Search ไม่สำเร็จ"
