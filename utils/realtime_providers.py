# utils/realtime_providers.py
# -*- coding: utf-8 -*-
"""
Realtime providers (เสถียร + ปลอดภัย) พร้อม TTL cache, retry, และ graceful fallback

ฟีเจอร์หลัก
- HTTP retry (รองรับ 429 / Retry-After) + exponential backoff
- TTL cache แบบเธรดเซฟ (ไม่แคช error ตามค่าเริ่มต้น)
- LIVE_MODE: ปิด live จะยืด TTL อัตโนมัติ ลดการยิงซ้ำเวลา dev/test
- Providers:
  • FX (OpenExchangeRates → exchangerate.host)
  • Weather (OpenWeatherMap)
  • Crypto (CoinGecko simple price + แมปเหรียญยอดนิยม)
  • Stocks (Finnhub → Yahoo Finance)
  • Gold (goldapi.io → ไม่มีคีย์จะคืน None)
  • Oil (ไทย — เป็น placeholder ให้เชื่อมต่อแหล่งข้อมูลของคุณ)

รูปแบบค่าที่คืน
- ทุกฟังก์ชันคืน dict ที่มีคีย์มาตรฐาน:
  {
    "ok": bool,            # สำเร็จหรือไม่
    "source": str,         # แหล่งข้อมูลที่ตอบ
    "...": any,            # ข้อมูลเฉพาะของ provider (รักษาชื่อคีย์เดิมให้มากที่สุด)
    "error": str|None      # ข้อความผิดพลาด (ถ้ามี)
  }
- เพื่อความเข้ากันได้เก่า: คีย์เดิม เช่น "rate", "price", "temp" จะยังถูกระบุในกรณี ok=True

ปรับแต่งผ่าน ENV
- LIVE_MODE=1                         (ดีฟอลต์ 1)
- HTTP_TIMEOUT_SEC=8
- HTTP_RETRIES=2                      (รวมพยายาม = 1 + HTTP_RETRIES)
- HTTP_BACKOFF_BASE_SEC=0.4
- CACHE_RESPECT_ERRORS=0              (0=อย่าแคช error, 1=แคช error ได้)
- DEFAULT_UA="..."                    (ตั้งค่า User-Agent)
- OPENWEATHER_API_KEY, OXR_APP_ID, FINNHUB_KEY, GOLDAPI_KEY

หมายเหตุ
- บาง provider ต้องระบุค่า input ที่สมเหตุผล (เช่น crypto ใช้ id CoinGecko — มีแมปยอดนิยมให้)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Callable, Tuple
import os
import time
import json
import math
import threading
import requests

# -------------------- Config --------------------
LIVE_MODE = os.getenv("LIVE_MODE", "1") == "1"
TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "8"))
RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
BACKOFF_BASE = float(os.getenv("HTTP_BACKOFF_BASE_SEC", "0.4"))
CACHE_RESPECT_ERRORS = os.getenv("CACHE_RESPECT_ERRORS", "0") == "1"

# API keys
OXR_APP_ID = os.getenv("OXR_APP_ID", "")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "")
OPENWEATHER = os.getenv("OPENWEATHER_API_KEY", "")
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY", "")

# HTTP defaults
DEFAULT_UA = os.getenv(
    "DEFAULT_UA",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
_DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "th,en-US;q=0.9,en;q=0.8",
}

# CoinGecko base
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# แมปสัญลักษณ์ยอดนิยม (ให้รับ 'BTC', 'ETH' ฯลฯ ได้)
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

_session = requests.Session()

# -------------------- Logging --------------------
def _log(tag: str, **kw):
    try:
        print(f"[realtime_providers] {tag} :: " + json.dumps(kw, ensure_ascii=False))
    except Exception:
        print(f"[realtime_providers] {tag} :: {kw}")

# -------------------- TTL Cache (thread-safe) --------------------
class TTLCache:
    def __init__(self):
        self._m: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, k: str) -> Optional[Any]:
        with self._lock:
            v = self._m.get(k)
            if not v:
                return None
            exp, data = v
            if time.time() > exp:
                self._m.pop(k, None)
                return None
            return data

    def set(self, k: str, data: Any, ttl: int):
        with self._lock:
            self._m[k] = (time.time() + ttl, data)

_cache = TTLCache()

def _cache_get_or(key: str, ttl: int, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    # ในโหมด non-live ให้ยืด TTL เพื่อประหยัดการยิงซ้ำ
    if not LIVE_MODE:
        ttl = max(ttl, 600)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    data = fn()
    # โดยปริยาย: อย่าแคช error เพื่อลองใหม่ครั้งถัดไป (ยกเว้นผู้ใช้เปิด CACHE_RESPECT_ERRORS)
    if data and (data.get("ok") or CACHE_RESPECT_ERRORS):
        _cache.set(key, data, ttl)
    return data

# -------------------- HTTP helpers (retry+backoff+429) --------------------
def _backoff_sleep(attempt: int, retry_after: Optional[float] = None):
    if retry_after is not None:
        time.sleep(min(float(retry_after), 3.0))
        return
    delay = BACKOFF_BASE * (2 ** max(0, attempt - 1)) + 0.05 * attempt
    time.sleep(min(delay, 2.5))

def _extract_retry_after(resp: requests.Response) -> Optional[float]:
    # รองรับทั้ง header และ body json
    try:
        if "Retry-After" in resp.headers:
            return float(resp.headers["Retry-After"])
    except Exception:
        pass
    try:
        j = resp.json()
        val = j.get("parameters", {}).get("retry_after")
        if val is not None:
            return float(val)
    except Exception:
        pass
    return None

def _http_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[requests.Response]:
    last_err = None
    _headers = dict(_DEFAULT_HEADERS)
    if headers:
        _headers.update(headers)
    for attempt in range(1, RETRIES + 2):
        try:
            r = _session.get(url, params=params or {}, headers=_headers, timeout=TIMEOUT)
            if r.status_code == 429:
                ra = _extract_retry_after(r)
                _log("HTTP_429", url=url, attempt=attempt, retry_after=ra)
                if attempt <= RETRIES:
                    _backoff_sleep(attempt, ra)
                    continue
            if r.ok:
                return r
            _log("HTTP_ERROR", url=url, status=r.status_code, text=r.text[:200])
            if attempt <= RETRIES:
                _backoff_sleep(attempt)
        except requests.RequestException as e:
            last_err = e
            _log("HTTP_EXCEPTION", url=url, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _backoff_sleep(attempt)
        except Exception as e:
            last_err = e
            _log("HTTP_UNKNOWN", url=url, attempt=attempt, err=str(e))
            if attempt <= RETRIES:
                _backoff_sleep(attempt)
    _log("HTTP_GIVEUP", url=url, last_err=str(last_err) if last_err else None)
    return None

def _fetch_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    r = _http_get(url, params=params, headers=headers)
    if not r:
        return {"ok": False, "error": "network_error", "source": "http"}
    try:
        return {"ok": True, "data": r.json(), "source": "http"}
    except Exception:
        return {"ok": True, "data": {"raw": r.text}, "source": "http"}

# -------------------- Format helpers --------------------
def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return None

def _kmh_from_ms(ms: Any) -> Optional[float]:
    v = _safe_float(ms)
    return round(v * 3.6, 1) if v is not None else None

# -------------------- Providers --------------------
# 1) FX rate (base/quote)
def get_fx_rate(base: str, quote: str) -> Dict[str, Any]:
    base = (base or "").upper().strip()
    quote = (quote or "").upper().strip()
    if not base or not quote:
        return {"ok": False, "source": "validation", "error": "invalid_currency"}

    key = f"fx:{base}:{quote}"

    def _call() -> Dict[str, Any]:
        # Primary: OpenExchangeRates
        if OXR_APP_ID:
            r = _fetch_json(
                "https://openexchangerates.org/api/latest.json",
                params={"app_id": OXR_APP_ID, "base": base},
            )
            if r.get("ok"):
                rates = (r["data"] or {}).get("rates", {})
                val = _safe_float(rates.get(quote))
                if val is not None:
                    return {"ok": True, "source": "OXR", "base": base, "quote": quote, "rate": val, "error": None}
        # Fallback: exchangerate.host
        r = _fetch_json(
            "https://api.exchangerate.host/latest",
            params={"base": base, "symbols": quote},
        )
        if r.get("ok"):
            rates = (r["data"] or {}).get("rates", {})
            val = _safe_float(rates.get(quote))
            if val is not None:
                return {"ok": True, "source": "exchangerate.host", "base": base, "quote": quote, "rate": val, "error": None}
        return {"ok": False, "source": "unknown", "base": base, "quote": quote, "rate": None, "error": "no_rate"}

    # FX เคลื่อนไหวไว: TTL 60s
    return _cache_get_or(key, ttl=60, fn=_call)

# 2) Weather (OpenWeatherMap)
def get_weather(
    lat: float | None = None,
    lon: float | None = None,
    q: str | None = None,
    units: str = "metric",
    lang: str = "th",
) -> Dict[str, Any]:
    if not OPENWEATHER:
        return {"ok": False, "source": "validation", "error": "missing_OPENWEATHER_API_KEY"}

    if (lat is None or lon is None) and not q:
        return {"ok": False, "source": "validation", "error": "missing_location"}

    units = units if units in ("metric", "imperial", "standard") else "metric"
    key = f"wx:{lat}:{lon}:{q}:{units}:{lang}"

    def _call() -> Dict[str, Any]:
        params: Dict[str, Any] = {"appid": OPENWEATHER, "units": units, "lang": lang}
        if lat is not None and lon is not None:
            params.update({"lat": lat, "lon": lon})
        else:
            params.update({"q": q})

        r = _fetch_json("https://api.openweathermap.org/data/2.5/weather", params=params)
        if not r.get("ok"):
            return {"ok": False, "source": "openweather", "error": r.get("error", "network_error")}

        data = r["data"] or {}
        main = data.get("main", {}) or {}
        wx = (data.get("weather") or [{}])[0] or {}
        wind = data.get("wind", {}) or {}

        result = {
            "ok": True,
            "source": "openweather",
            "name": data.get("name") or (q or "-"),
            "temp": _safe_float(main.get("temp")),
            "feels_like": _safe_float(main.get("feels_like")),
            "humidity": _safe_float(main.get("humidity")),
            "desc": wx.get("description"),
            "wind_kmh": _kmh_from_ms(wind.get("speed")),
            "error": None,
        }
        return result

    # อากาศเปลี่ยนช้ากว่า: TTL ~ 10 นาที
    return _cache_get_or(key, ttl=600, fn=_call)

# 3) Crypto (CoinGecko simple price)
def _resolve_cg_id(symbol_or_id: str) -> Optional[str]:
    if not symbol_or_id:
        return None
    s_up = symbol_or_id.strip().upper()
    if s_up in _CG_COMMON:
        return _CG_COMMON[s_up]
    s_id = symbol_or_id.strip().lower()
    # ยอมรับ id โดยตรง เช่น "bitcoin", "the-open-network"
    if all(ch.isalnum() or ch in "-_" for ch in s_id) and len(s_id) >= 3:
        return s_id
    return None

def get_crypto_price(symbol_or_id: str, vs: str = "USD") -> Dict[str, Any]:
    cid = _resolve_cg_id(symbol_or_id)
    if not cid:
        return {"ok": False, "source": "coingecko", "error": f"unsupported_symbol:{symbol_or_id}"}

    vs_l = (vs or "USD").lower()
    key = f"cg:{cid}:{vs_l}"

    def _call() -> Dict[str, Any]:
        r = _fetch_json(
            f"{COINGECKO_BASE}/simple/price",
            params={"ids": cid, "vs_currencies": vs_l, "include_24hr_change": "true"},
        )
        if not r.get("ok"):
            return {"ok": False, "source": "coingecko", "error": r.get("error", "network_error")}
        js = r["data"] or {}
        row = js.get(cid) or {}
        price = _safe_float(row.get(vs_l))
        chg = row.get(f"{vs_l}_24h_change")
        chg_float = _safe_float(chg)
        return {
            "ok": price is not None,
            "source": "coingecko",
            "symbol": symbol_or_id.upper(),
            "coin_id": cid,
            "vs": vs.upper(),
            "price": price,
            "change_24h": chg_float,
            "error": None if price is not None else "no_price",
        }

    # คริปโตเคลื่อนไหวไว: TTL 10s
    return _cache_get_or(key, ttl=10, fn=_call)

# 4) Stocks (Finnhub → Yahoo)
def get_stock_quote(symbol: str) -> Dict[str, Any]:
    sym = (symbol or "").upper().strip()
    if not sym:
        return {"ok": False, "source": "validation", "error": "missing_symbol"}

    key = f"st:{sym}"

    def _call() -> Dict[str, Any]:
        # Primary: Finnhub
        if FINNHUB_KEY:
            r = _fetch_json("https://finnhub.io/api/v1/quote", params={"symbol": sym, "token": FINNHUB_KEY})
            if r.get("ok"):
                js = r["data"] or {}
                # Finnhub structure: c=current, o=open, h=high, l=low
                if "c" in js:
                    return {
                        "ok": True,
                        "source": "finnhub",
                        "symbol": sym,
                        "price": _safe_float(js.get("c")),
                        "open": _safe_float(js.get("o")),
                        "high": _safe_float(js.get("h")),
                        "low": _safe_float(js.get("l")),
                        "error": None,
                    }
        # Fallback: Yahoo Finance
        r = _fetch_json("https://query1.finance.yahoo.com/v7/finance/quote", params={"symbols": sym})
        if r.get("ok"):
            js = r["data"] or {}
            rows = (js.get("quoteResponse") or {}).get("result") or []
            if rows:
                q = rows[0] or {}
                return {
                    "ok": True,
                    "source": "yahoo",
                    "symbol": sym,
                    "price": _safe_float(q.get("regularMarketPrice")),
                    "open": _safe_float(q.get("regularMarketOpen")),
                    "high": _safe_float(q.get("regularMarketDayHigh")),
                    "low": _safe_float(q.get("regularMarketDayLow")),
                    "error": None,
                }
        return {"ok": False, "source": "unknown", "symbol": sym, "price": None, "error": "no_quote"}

    # TTL 30s (ช่วงตลาดเปิด)
    return _cache_get_or(key, ttl=30, fn=_call)

# 5) Gold spot (goldapi.io)
def get_gold_price_spot() -> Dict[str, Any]:
    if not GOLDAPI_KEY:
        return {"ok": False, "source": "goldapi", "price": None, "currency": "USD", "error": "missing_GOLDAPI_KEY"}

    key = "gold:spot"

    def _call() -> Dict[str, Any]:
        r = _fetch_json("https://www.goldapi.io/api/XAU/USD", headers={"x-access-token": GOLDAPI_KEY})
        if not r.get("ok"):
            return {"ok": False, "source": "goldapi", "price": None, "currency": "USD", "error": r.get("error", "network_error")}
        js = r["data"] or {}
        price = _safe_float(js.get("price"))
        return {
            "ok": price is not None,
            "source": "goldapi",
            "price": price,
            "currency": "USD",
            "error": None if price is not None else "no_price",
        }

    # ทองไม่ได้วิ่งวินาทีต่อวินาที: TTL 60s
    return _cache_get_or(key, ttl=60, fn=_call)

# 6) Oil (Thailand) — placeholder ให้เชื่อมต่อแหล่งจริงของคุณ
def get_oil_price_th() -> Dict[str, Any]:
    """
    เชื่อมต่อแหล่งข้อมูลราคาน้ำมันไทยของคุณที่นี่ แล้วปรับ TTL ให้เหมาะสม
    โครงสร้างผลลัพธ์ที่แนะนำ:
    {
        "ok": True,
        "source": "your-provider",
        "items": [
            {"name": "ดีเซล", "price": 30.94, "unit": "THB/L"},
            {"name": "แก๊สโซฮอล์ 95", "price": 37.50, "unit": "THB/L"},
            ...
        ],
        "error": None
    }
    """
    key = "oil:th"

    def _call() -> Dict[str, Any]:
        # TODO: ต่อ API/สครัปของจริง
        return {
            "ok": True,
            "source": "manual-or-internal",
            "items": [],
            "error": None,
        }

    # TTL ยาว ๆ ~ 12 ชั่วโมง (อัปเดตรายวัน)
    return _cache_get_or(key, ttl=43200, fn=_call)
