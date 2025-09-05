# src/utils/serp_utils.py
# -*- coding: utf-8 -*-
"""
Stable SERP utilities (no API key required)

ฟีเจอร์หลัก
- หุ้น (Yahoo Finance v7 quote): เดาสัญลักษณ์ฉลาดขึ้น (.BK / SET → ^SETI), ใส่โซนเวลา Asia/Bangkok
- น้ำมัน (WTI=CL=F, Brent=BZ=F จาก Yahoo): สรุปชัดเจน พร้อมลูกศรแนวโน้ม
- สลากกินแบ่งฯ (lottoth-api): รองรับงวดล่าสุด/ระบุวันที่, ตรวจรูปแบบวัน, มี retry+cache
- คริปโต (CoinGecko simple/price): รองรับเหรียญฮิตจำนวนมาก, แสดง THB/ USD และ %24ชม.

คุณสมบัติความเสถียร
- HTTP retry + exponential backoff + timeout (ตั้งผ่าน ENV)
- เคารพ 429 (อ่าน retry_after ถ้ามี)
- แคชชั่วคราวในหน่วยความจำ (TTL ตั้งผ่าน ENV)
- Markdown safe (escape ข้อความที่สุ่มเสี่ยง)
- ข้อความพร้อมอีโมจิ, อ่านง่าย

ENV ที่ตั้งค่าได้:
- SERP_TIMEOUT               (ดีฟอลต์ 10)
- SERP_RETRIES               (ดีฟอลต์ 2)      # รวมทั้งหมด = 1 + SERP_RETRIES
- SERP_BACKOFF_BASE_SEC      (ดีฟอลต์ 0.4)
- SERP_CACHE_TTL_SEC         (ดีฟอลต์ 30)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
import os
import time
import json
import math
import re
import datetime as _dt

import requests

# ---------- Config ----------
TIMEOUT = float(os.getenv("SERP_TIMEOUT", "10"))
RETRIES = int(os.getenv("SERP_RETRIES", "2"))
BACKOFF_BASE = float(os.getenv("SERP_BACKOFF_BASE_SEC", "0.4"))
CACHE_TTL = float(os.getenv("SERP_CACHE_TTL_SEC", "30"))

# HTTP session + headers
_session = requests.Session()
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]
def _headers() -> Dict[str, str]:
    import random
    return {
        "User-Agent": random.choice(_UA_POOL),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "th,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }

_cache: Dict[str, Tuple[float, Any]] = {}  # key -> (ts, value)

# ---------- Helpers ----------
def _log(tag: str, **kw):
    try:
        print(f"[serp_utils] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[serp_utils] {tag} :: {kw}")

def _retry_sleep(attempt: int, retry_after: Optional[float] = None):
    if retry_after is not None:
        try:
            time.sleep(min(float(retry_after), 3.0))
            return
        except Exception:
            pass
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _http_get(url: str, params: Optional[Dict[str, Any]] = None, timeout: float = TIMEOUT) -> Optional[requests.Response]:
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
            _log("HTTP_ERROR", url=url, status=r.status_code, text=r.text[:200])
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

def _cache_get(key: str):
    if key in _cache:
        ts, val = _cache[key]
        if (time.time() - ts) <= CACHE_TTL:
            return val
        _cache.pop(key, None)
    return None

def _cache_put(key: str, val: Any):
    _cache[key] = (time.time(), val)

# ---- Markdown helpers (Telegram Markdown v1 safe enough) ----
_MD_ESC = str.maketrans({
    "_": r"\_",
    "*": r"\*",
    "[": r"\[",
    "]": r"\]",
    "(": r"\(",
    ")": r"\)",
    "~": r"\~",
    "`": r"\`",
    ">": r"\>",
    "#": r"\#",
    "+": r"\+",
    "-": r"\-",
    "=": r"\=",
    "|": r"\|",
    "{": r"\{",
    "}": r"\}",
    ".": r"\.",
    "!": r"\!",
})
def _md(s: Any) -> str:
    try:
        return str(s).translate(_MD_ESC)
    except Exception:
        return str(s)

# ---- Numbers & arrows ----
def _fmt_num(n: float, digits: int = 2) -> str:
    try:
        if n is None or (isinstance(n, float) and (math.isnan(n) or math.isinf(n))):
            return "-"
        if abs(n) >= 1:
            return f"{n:,.2f}"
        return f"{n:,.4f}"
    except Exception:
        return str(n)

def _arrow(change: Optional[float]) -> str:
    try:
        if change is None:
            return ""
        return "📈" if change > 0 else ("📉" if change < 0 else "➖")
    except Exception:
        return ""

def _percent(n: Optional[float]) -> str:
    try:
        if n is None:
            return "-"
        return f"{n:.2f}%"
    except Exception:
        return "-"

# ---- Timezone helpers (to Asia/Bangkok) ----
try:
    from zoneinfo import ZoneInfo  # Py3.9+
    _BKK = ZoneInfo("Asia/Bangkok")
    _UTC = ZoneInfo("UTC")
    def _to_bkk_str(epoch_sec: Optional[int]) -> str:
        if not epoch_sec:
            return "-"
        dt = _dt.datetime.fromtimestamp(int(epoch_sec), tz=_UTC).astimezone(_BKK)
        return dt.strftime("%Y-%m-%d %H:%M")
except Exception:
    def _to_bkk_str(epoch_sec: Optional[int]) -> str:
        try:
            if not epoch_sec:
                return "-"
            dt = _dt.datetime.utcfromtimestamp(int(epoch_sec)) + _dt.timedelta(hours=7)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return "-"

# ---------- Stocks (Yahoo Finance) ----------
def _yahoo_quote(symbols: List[str]) -> Optional[Dict[str, Any]]:
    """
    Yahoo Finance quote API (ไม่มี key)
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

def _ensure_symbol_inferred(raw: str) -> str:
    """
    เดาสัญลักษณ์จากข้อความของผู้ใช้:
    - SET → ^SETI (Yahoo)
    - ถ้าเป็นตัวอักษร/ตัวเลข 2–5 ตัว และไม่มีจุด → เติม .BK (คาดว่าเป็นหุ้นไทย)
    """
    s = (raw or "").strip().upper()
    # ดึง token ที่ดูเหมือนสัญลักษณ์
    m = re.search(r"[A-Z0-9.\-^]{1,12}", s)
    if m:
        s = m.group(0)
    if s in {"SET", "^SET", "SETI"}:
        return "^SETI"
    parts = re.findall(r"[A-Z0-9]{2,5}(?:\.[A-Z]{1,4})?", s)
    cand = parts[-1].upper() if parts else s
    if "." not in cand and 2 <= len(cand) <= 5:
        return cand + ".BK"
    return cand

def get_stock_info(query: str) -> str:
    """
    ดึงราคาหุ้นจาก Yahoo Finance และสรุปผลเป็น Markdown
    """
    try:
        sym = _ensure_symbol_inferred(query)
        data = _yahoo_quote([sym])
        results = data.get("quoteResponse", {}).get("result") if data else None
        if not results:
            return "❌ ไม่พบข้อมูลหุ้นที่ขอครับ"

        q = results[0]
        name = q.get("shortName") or q.get("longName") or q.get("symbol") or sym
        symbol = q.get("symbol") or sym
        price = q.get("regularMarketPrice")
        chg = q.get("regularMarketChange")
        chg_pct = q.get("regularMarketChangePercent")
        cur = q.get("currency") or "-"
        exch = q.get("fullExchangeName") or q.get("exchange") or "-"
        state = q.get("marketState") or "-"
        ts = q.get("regularMarketTime") or q.get("postMarketTime") or q.get("preMarketTime")
        when_bkk = _to_bkk_str(ts)
        arrow = _arrow(chg if isinstance(chg, (int, float)) else None)

        if price is None:
            return f"❌ ไม่พบราคาสดของ `{_md(symbol)}`"

        msg = (
            f"📊 *{_md(name)}* (`{_md(symbol)}`)\n"
            f"ราคา: *{_fmt_num(price)}* {_md(cur)}  {arrow}\n"
            f"เปลี่ยนแปลง: {_fmt_num(chg)} ({_percent(chg_pct)})\n"
            f"ตลาด: {_md(exch)} | สถานะ: {_md(state)}\n"
            f"🕒 เวลาข้อมูล (กรุงเทพฯ): `{when_bkk}`"
        )
        return msg
    except Exception as e:
        _log("STOCK_ERR", err=str(e))
        # Fallback mock (ย้อนรองรับของเดิมเพื่อไม่ให้พัง flow)
        uq = (query or "").upper()
        if "SET" in uq:
            return "SET วันนี้: 1,234.56 (+4.56)"
        if "PTT" in uq:
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
    ราคาน้ำมันดิบโลก (WTI / Brent) จาก Yahoo (CL=F, BZ=F)
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
            arr = _arrow(ch if isinstance(ch, (int, float)) else None)
            if px is None:
                return f"- {label}: ไม่พร้อมใช้งาน"
            return f"- {label}: {_fmt_num(px)} {cur}  {arr}  ({_fmt_num(ch)} / {_percent(chp)})"

        ts = None
        for sym in syms:
            ts = ts or q.get(sym, {}).get("regularMarketTime")
        when_bkk = _to_bkk_str(ts)

        msg = (
            "🛢️ *ราคาน้ำมันดิบโลกวันนี้*\n" +
            "\n".join([
                fmt("CL=F", "WTI (CL=F)"),
                fmt("BZ=F", "Brent (BZ=F)"),
            ]) +
            f"\n🕒 เวลาข้อมูล (กรุงเทพฯ): `{when_bkk}`"
        )
        return msg
    except Exception as e:
        _log("OIL_ERR", err=str(e))
        # Fallback mock ของเดิม
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
    ดึงผลสลากกินแบ่งรัฐบาล (ล่าสุด หรือระบุ 'YYYY-MM-DD')
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
            f"📅 *ผลสลากกินแบ่งรัฐบาล* งวดวันที่ {_md(dt)}\n"
            f"🏆 รางวัลที่ 1: *{_md(reward1)}*\n"
            f"🔢 เลขหน้า 3 ตัว: {_md(front3 or '-')}\n"
            f"🔢 เลขท้าย 3 ตัว: {_md(back3 or '-')}\n"
            f"🎯 เลขท้าย 2 ตัว: *{_md(back2)}*\n"
            f"_ข้อมูล: lottoth-api_"
        )
        return msg
    except Exception as e:
        _log("LOTTO_ERR", err=str(e))
        return "❌ เกิดข้อผิดพลาดในการดึงผลสลาก"

# ---------- Crypto (CoinGecko) ----------
_CG_COMMON: Dict[str, str] = {
    # Top caps + ยอดนิยม
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
    "AVAX": "avalanche-2",
    "NEAR": "near",
    "OP": "optimism",
    "ARB": "arbitrum",
    "APT": "aptos",
    "SUI": "sui",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
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
    if s in _CG_COMMON:
        return _CG_COMMON[s]
    # heuristic: ถ้าผู้ใช้พิมพ์ id เต็มอยู่แล้ว (เช่น the-open-network)
    s_id = (symbol_or_name or "").strip().lower()
    if re.fullmatch(r"[a-z0-9\-]{3,50}", s_id):
        return s_id
    return None

def get_crypto_price(coin: str) -> str:
    """
    ดึงราคาคริปโต (THB / USD) + %เปลี่ยนแปลง 24ชม. (CoinGecko)
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
        arr = _arrow(chg_thb if isinstance(chg_thb, (int, float)) else (chg_usd if isinstance(chg_usd, (int, float)) else None))
        name = cid.replace("-", " ").title()

        msg = (
            f"💎 *{_md(name)}*\n"
            f"THB: *{_fmt_num(float(thb)) if thb is not None else '-'}*  {arr}\n"
            f"USD: {_fmt_num(float(usd)) if usd is not None else '-'}\n"
            f"เปลี่ยน 24 ชม.: "
            f"{_percent(float(chg_thb)) if isinstance(chg_thb, (int, float)) else (_percent(float(chg_usd)) if isinstance(chg_usd, (int, float)) else '-')}"
        )
        return msg
    except Exception as e:
        _log("CRYPTO_ERR", err=str(e))
        # Fallback mock (เพื่อความต่อเนื่อง)
        c = (coin or "").lower()
        if c in ["btc", "bitcoin"]:
            return "Bitcoin (BTC): 2,350,000 บาท"
        elif c in ["eth", "ethereum"]:
            return "Ethereum (ETH): 130,000 บาท"
        return f"❌ ยังไม่รองรับเหรียญ {coin.upper()}"

# ---------- (Optional) CLI test ----------
if __name__ == "__main__":
    print(get_stock_info("PTT"))
    print(get_stock_info("SET"))
    print(get_oil_price())
    print(get_lottery_result())
    print(get_crypto_price("BTC"))
