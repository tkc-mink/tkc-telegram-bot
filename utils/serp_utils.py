# src/utils/serp_utils.py
# -*- coding: utf-8 -*-
"""
Stable SERP utilities (no API key required)
- หุ้น: ดึงจาก Yahoo Finance quote API (server-side JSON, ไม่ต้องใช้ key)
- น้ำมัน: WTI(CL=F) / Brent(BZ=F) จาก Yahoo Finance
- สลากกินแบ่งฯ: lottoth-api (มี retry + ตรวจรูปแบบวันที่)
- คริปโต: CoinGecko (simple price) + แมปสัญลักษณ์ยอดนิยม

คุณสมบัติความเสถียร:
- HTTP retry + exponential backoff + timeout กำหนดได้ผ่าน ENV
- เคารพ 429 (retry_after ถ้ามี)
- แคชชั่วคราวในหน่วยความจำ ลดการยิงซ้ำ (TTL ตั้งได้)
- จัดรูปข้อความสวยงาม (Markdown) พร้อมอีโมจิ
- Fallback เป็นข้อความ mock เมื่อ API ภายนอกล้มเหลว

ENV ที่ตั้งค่าได้:
- SERP_TIMEOUT                 (ดีฟอลต์ 10)
- SERP_RETRIES                 (ดีฟอลต์ 2)      # รวมทั้งหมด = 1+SERP_RETRIES
- SERP_BACKOFF_BASE_SEC        (ดีฟอลต์ 0.4)
- SERP_CACHE_TTL_SEC           (ดีฟอลต์ 30)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
import os
import time
import json
import math
import re

import requests

# ---------- Config ----------
TIMEOUT = float(os.getenv("SERP_TIMEOUT", "10"))
RETRIES = int(os.getenv("SERP_RETRIES", "2"))
BACKOFF_BASE = float(os.getenv("SERP_BACKOFF_BASE_SEC", "0.4"))
CACHE_TTL = float(os.getenv("SERP_CACHE_TTL_SEC", "30"))

_session = requests.Session()
_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (ts, value)

# ---------- Helpers ----------
def _log(tag: str, **kw):
    try:
        print(f"[serp_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[serp_utils] {tag} :: {kw}")

def _retry_sleep(attempt: int, retry_after: Optional[float] = None):
    if retry_after is not None:
        time.sleep(min(float(retry_after), 3.0))
        return
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _http_get(url: str, params: Optional[Dict[str, Any]] = None, timeout: float = TIMEOUT) -> Optional[requests.Response]:
    last_err = None
    for attempt in range(1, RETRIES + 2):
        try:
            r = _session.get(url, params=params or {}, timeout=timeout)
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
            _log("HTTP_ERROR", url=url, status=r.status_code, text=r.text[:200])
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except requests.RequestException as e:
            _log("HTTP_EXCEPTION", url=url, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _retry_sleep(attempt)
        except Exception as e:
            _log("HTTP_UNKNOWN", url=url, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _retry_sleep(attempt)
    _log("HTTP_GIVEUP", url=url, last_err=str(last_err) if last_err else None)
    return None

def _cache_get(key: str):
    if key in _cache:
        ts, val = _cache[key]
        if (time.time() - ts) <= CACHE_TTL:
            return val
        _cache.pop(key, None)
    return None

def _cache_put(key: str, val: Any):
    _cache[key] = (time.time(), val)

def _fmt_num(n: float, digits: int = 2) -> str:
    try:
        if n is None or (isinstance(n, float) and (math.isnan(n) or math.isinf(n))):
            return "-"
        # ตัดทศนิยมอัจฉริยะ: ราคาใหญ่ใช้ 2 ตำแหน่ง, เล็กใช้ 4
        if abs(n) >= 1000:
            return f"{n:,.2f}"
        if abs(n) >= 1:
            return f"{n:,.2f}"
        return f"{n:,.4f}"
    except Exception:
        return str(n)

def _arrow(change: float) -> str:
    if change is None:
        return ""
    return "📈" if change > 0 else ("📉" if change < 0 else "➖")

def _percent(n: float) -> str:
    try:
        return f"{n:.2f}%"
    except Exception:
        return "-"

def _ensure_symbol_inferred(raw: str) -> str:
    """
    พยายามเดาสัญลักษณ์จากข้อความที่ผู้ใช้พิมพ์:
    - ถ้าเป็น SET ให้แมปเป็น ^SETI (Yahoo)
    - ถ้าเป็นตัวอักษร 2–5 ตัว ไม่มีจุด → อาจเป็นหุ้นไทย เติม .BK
    """
    s = (raw or "").strip().upper()
    # ดึงโทเค็นที่ดูเหมือนสัญลักษณ์ที่สุด (ตัวเลข/ตัวอักษร/จุด/ขีด)
    m = re.search(r"[A-Z0-9.\-^]{1,12}", s)
    if m:
        s = m.group(0)
    if s in {"SET", "^SET", "SETI"}:
        return "^SETI"
    # กรณีผู้ใช้พิมพ์ "หุ้น PTT" ให้ดึง PTT
    parts = re.findall(r"[A-Z0-9]{2,5}(?:\.[A-Z]{1,4})?", s)
    if parts:
        cand = parts[-1].upper()
    else:
        cand = s
    if "." not in cand and 2 <= len(cand) <= 5:
        # คาดว่าเป็นหุ้นไทย
        return cand + ".BK"
    return cand

# ---------- Stocks (Yahoo Finance) ----------
def _yahoo_quote(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    เรียก Yahoo Finance quote API แบบรวดเดียว
    """
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    params = {"symbols": ",".join(symbols)}
    cache_key = f"yq:{params['symbols']}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    resp = _http_get(url, params=params)
    if not resp:
        return None
    try:
        data = resp.json()
        _cache_put(cache_key, data)
        return data
    except Exception as e:
        _log("YQ_JSON_ERR", err=str(e))
        return None

def get_stock_info(query: str) -> str:
    """
    ดึงราคาหุ้นจาก Yahoo Finance
    - รองรับ SET → ^SETI, หุ้นไทยเดาส่วนขยาย .BK ถ้าไม่ระบุ
    """
    try:
        sym = _ensure_symbol_inferred(query)
        data = _yahoo_quote([sym])
        if not data or not data.get("quoteResponse", {}).get("result"):
            return "❌ ไม่พบข้อมูลหุ้นที่ขอครับ"

        q = data["quoteResponse"]["result"][0]
        name = q.get("shortName") or q.get("longName") or q.get("symbol") or sym
        symbol = q.get("symbol") or sym
        price = q.get("regularMarketPrice")
        chg = q.get("regularMarketChange")
        chg_pct = q.get("regularMarketChangePercent")
        cur = q.get("currency") or "-"
        exch = q.get("fullExchangeName") or q.get("exchange") or "-"
        state = q.get("marketState") or "-"
        arrow = _arrow(chg if isinstance(chg, (int, float)) else 0.0)

        if price is None:
            return f"❌ ไม่พบราคาสดของ {symbol}"

        msg = (
            f"📊 *{name}* (`{symbol}`)\n"
            f"ราคา: *{_fmt_num(price)}* {cur}  {arrow}\n"
            f"เปลี่ยนแปลง: {_fmt_num(chg)} ({_percent(chg_pct)})\n"
            f"ตลาด: {exch} | สถานะ: {state}"
        )
        return msg
    except Exception as e:
        _log("STOCK_ERR", err=str(e))
        # Fallback mock (เดิม)
        if "SET" in query.upper():
            return "SET วันนี้: 1,234.56 (+4.56)"
        elif "PTT" in query.upper():
            return "PTT: 38.25 บาท (+0.25)"
        return "❌ ยังไม่รองรับหุ้นนี้"

# ---------- Oil (WTI/Brent via Yahoo) ----------
def _yahoo_quote_multi(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    data = _yahoo_quote(symbols)
    out: Dict[str, Dict[str, Any]] = {}
    if not data:
        return out
    for it in data.get("quoteResponse", {}).get("result", []):
        out[it.get("symbol", "?")] = it
    return out

def get_oil_price() -> str:
    """
    ราคาน้ำมันดิบโลก (WTI / Brent) จาก Yahoo (สัญลักษณ์: CL=F, BZ=F)
    """
    try:
        syms = ["CL=F", "BZ=F"]
        q = _yahoo_quote_multi(syms)
        if not q:
            raise RuntimeError("yahoo empty")

        def fmt(sym: str, label: str) -> str:
            d = q.get(sym, {})
            px = d.get("regularMarketPrice")
            ch = d.get("regularMarketChange")
            chp = d.get("regularMarketChangePercent")
            cur = d.get("currency") or "USD"
            arr = _arrow(ch if isinstance(ch, (int, float)) else 0.0)
            if px is None:
                return f"- {label}: ไม่พร้อมใช้งาน"
            return f"- {label}: {_fmt_num(px)} {cur}  {arr}  ({_fmt_num(ch)} / {_percent(chp)})"

        msg = "🛢️ *ราคาน้ำมันดิบโลกวันนี้*\n" + "\n".join([
            fmt("CL=F", "WTI (CL=F)"),
            fmt("BZ=F", "Brent (BZ=F)"),
        ])
        return msg
    except Exception as e:
        _log("OIL_ERR", err=str(e))
        return (
            "ราคาน้ำมันวันนี้:\n"
            "- ดีเซล: 30.94\n"
            "- แก๊สโซฮอล์ 95: 37.50\n"
            "- E20: 36.34 บาท"
        )

# ---------- Lottery (lottoth-api) ----------
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _lottoth_latest_or_date(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if date and not _DATE_RE.match(date):
        return None
    url = "https://lottoth-api.vercel.app/api/latest" if not date else f"https://lottoth-api.vercel.app/api/dates/{date}"
    cache_key = f"lotto:{date or 'latest'}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    r = _http_get(url, timeout=TIMEOUT)
    if not r:
        return None
    try:
        data = r.json()
        _cache_put(cache_key, data)
        return data
    except Exception as e:
        _log("LOTTO_JSON_ERR", err=str(e))
        return None

def get_lottery_result(date: str = None) -> str:
    """
    ดึงผลสลากกินแบ่งรัฐบาลจริง (API: lottoth-api)
    - ถ้าไม่ระบุ date จะดึงงวดล่าสุด
    - ระบุ date รูปแบบ 'YYYY-MM-DD'
    """
    try:
        data = _lottoth_latest_or_date(date)
        if not data or not data.get("data"):
            return "❌ ไม่พบข้อมูลผลสลาก (API)"

        d = data["data"]
        dt = d.get("date", "-")
        reward1 = d.get("reward1", "-")
        front3 = " ".join(d.get("front3", []) or [])
        back3 = " ".join(d.get("back3", []) or [])
        back2 = d.get("back2", "-")

        msg = (
            f"📅 *ผลสลากกินแบ่งรัฐบาล* งวดวันที่ {dt}\n"
            f"🏆 รางวัลที่ 1: *{reward1}*\n"
            f"🔢 เลขหน้า 3 ตัว: {front3 or '-'}\n"
            f"🔢 เลขท้าย 3 ตัว: {back3 or '-'}\n"
            f"🎯 เลขท้าย 2 ตัว: *{back2}*\n"
            f"_ข้อมูล: lottoth-api_"
        )
        return msg
    except Exception as e:
        _log("LOTTO_ERR", err=str(e))
        return "❌ เกิดข้อผิดพลาดในการดึงผลสลาก"

# ---------- Crypto (CoinGecko) ----------
# แมปสัญลักษณ์ที่พบบ่อย → coin id ของ CoinGecko
_CG_COMMON: Dict[str, str] = {
    "BTC": "bitcoin", "XBT": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "USDT": "tether",
    "USDC": "usd-coin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TON": "the-open-network",
    "TRX": "tron",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "LTC": "litecoin",
}

def _coingecko_simple_price(ids: List[str], vs: List[str]) -> Optional[Dict[str, Any]]:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(ids),
        "vs_currencies": ",".join(vs),
        "include_24hr_change": "true",
    }
    cache_key = f"cg:{params['ids']}:{params['vs_currencies']}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    r = _http_get(url, params=params, timeout=TIMEOUT)
    if not r:
        return None
    try:
        data = r.json()
        _cache_put(cache_key, data)
        return data
    except Exception as e:
        _log("CG_JSON_ERR", err=str(e))
        return None

def _resolve_coin_id(symbol_or_name: str) -> Optional[str]:
    s = (symbol_or_name or "").strip().upper()
    # match common
    if s in _CG_COMMON:
        return _CG_COMMON[s]
    # heuristic: ถ้าผู้ใช้พิมพ์ชื่อเต็มของ id
    s_id = (symbol_or_name or "").strip().lower()
    if re.fullmatch(r"[a-z0-9\-]{3,50}", s_id):
        return s_id
    return None  # เพื่อความเสถียร เราไม่ยิง /search เพิ่ม (ลด rate limit)

def get_crypto_price(coin: str) -> str:
    """
    ดึงราคาคริปโตผ่าน CoinGecko (THB/USDT) + เปอร์เซ็นต์ 24 ชม.
    รองรับสัญลักษณ์ยอดนิยม (BTC/ETH/BNB/…)
    """
    try:
        cid = _resolve_coin_id(coin)
        if not cid:
            c = (coin or "").upper()
            if c in ["BTC", "BITCOIN"]:
                cid = "bitcoin"
            elif c in ["ETH", "ETHEREUM"]:
                cid = "ethereum"
            else:
                return f"❌ ยังไม่รองรับเหรียญ {c}"
        data = _coingecko_simple_price([cid], ["thb", "usd"])
        if not data or cid not in data:
            return f"❌ ไม่พบข้อมูลราคาของ {coin.upper()}"

        row = data[cid]
        thb = row.get("thb"); usd = row.get("usd")
        chg_thb = row.get("thb_24h_change"); chg_usd = row.get("usd_24h_change")
        arr = _arrow(chg_thb if isinstance(chg_thb, (int, float)) else (chg_usd or 0.0))
        name = cid.replace("-", " ").title()

        msg = (
            f"💎 *{name}*\n"
            f"THB: *{_fmt_num(float(thb)) if thb is not None else '-'}*  {arr}\n"
            f"USD: {_fmt_num(float(usd)) if usd is not None else '-'}\n"
            f"เปลี่ยน 24 ชม.: "
            f"{_percent(float(chg_thb)) if isinstance(chg_thb, (int, float)) else (_percent(float(chg_usd)) if isinstance(chg_usd, (int, float)) else '-')}"
        )
        return msg
    except Exception as e:
        _log("CRYPTO_ERR", err=str(e))
        # Fallback mock (เดิม)
        c = (coin or "").lower()
        if c in ["btc", "bitcoin"]:
            return "Bitcoin (BTC): 2,350,000 บาท"
        elif c in ["eth", "ethereum"]:
            return "Ethereum (ETH): 130,000 บาท"
        return f"❌ ยังไม่รองรับเหรียญ {coin.upper()}"
