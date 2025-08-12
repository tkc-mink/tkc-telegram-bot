# utils/realtime_providers.py
# -*- coding: utf-8 -*-
"""
Realtime providers + TTL cache + graceful fallback
- FX (THB/LAK เป็นต้น)
- Weather (OpenWeather)
- Crypto (CoinGecko)
- Stocks (Finnhub -> Yahoo fallback แบบง่าย)
- Gold (GoldAPI -> fallback ชั่วคราวเป็น None)
- Oil (ที่ไทยอัปเดตรายวัน — ใช้ cache ยาวขึ้น)
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import os, time, json, requests

LIVE_MODE = os.getenv("LIVE_MODE", "1") == "1"
TIMEOUT   = float(os.getenv("HTTP_TIMEOUT_SEC", "8"))

# --- API keys (ใส่ได้ตามสะดวก) ---
OXR_APP_ID     = os.getenv("OXR_APP_ID", "")          # OpenExchangeRates (ทางการ)
FINNHUB_KEY    = os.getenv("FINNHUB_KEY", "")
OPENWEATHER    = os.getenv("OPENWEATHER_API_KEY", "")
GOLDAPI_KEY    = os.getenv("GOLDAPI_KEY", "")         # goldapi.io
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# ------------- Tiny TTL cache -------------
class TTLCache:
    def __init__(self): self._m: Dict[str, Any] = {}
    def get(self, k: str) -> Optional[Any]:
        v = self._m.get(k)
        if not v: return None
        exp, data = v
        if time.time() > exp:
            self._m.pop(k, None); return None
        return data
    def set(self, k: str, data: Any, ttl: int): self._m[k] = (time.time() + ttl, data)

_cache = TTLCache()

def _fetch_json(url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None):
    r = requests.get(url, params=params or {}, headers=headers or {}, timeout=TIMEOUT)
    r.raise_for_status()
    try: return r.json()
    except Exception: return {"raw": r.text}

def _cache_get_or(urlkey: str, ttl: int, fn):
    if not LIVE_MODE:
        # โหมดไม่สด: ให้ค่าแคชเดิมถ้ามี หรือเรียกหนึ่งครั้งแล้วเก็บยาว ๆ
        ttl = max(ttl, 600)
    v = _cache.get(urlkey)
    if v is not None: return v
    data = fn()
    _cache.set(urlkey, data, ttl)
    return data

# ------------- Providers -------------

# FX rate (คู่สกุลเงิน เช่น THB/LAK, USD/LAK)
def get_fx_rate(base: str, quote: str) -> Dict[str, Any]:
    base, quote = base.upper(), quote.upper()
    key = f"fx:{base}:{quote}"
    def _call():
        # Primary: OpenExchangeRates
        if OXR_APP_ID:
            url = "https://openexchangerates.org/api/latest.json"
            js = _fetch_json(url, params={"app_id": OXR_APP_ID, "base": base})
            rate = js.get("rates", {}).get(quote)
            if rate: return {"base": base, "quote": quote, "rate": float(rate), "source": "OXR"}
        # Fallback: exchangerate.host (ฟรี)
        url = "https://api.exchangerate.host/latest"
        js = _fetch_json(url, params={"base": base, "symbols": quote})
        rate = js.get("rates", {}).get(quote)
        if rate: return {"base": base, "quote": quote, "rate": float(rate), "source": "exchangerate.host"}
        return {"base": base, "quote": quote, "rate": None, "source": "unknown"}
    # FX เปลี่ยนเร็ว: TTL ~ 60s
    return _cache_get_or(key, ttl=60, fn=_call)

# Weather (โดย lat/lon หรือ q=city)
def get_weather(lat: float | None = None, lon: float | None = None, q: str | None = None, units: str = "metric") -> Dict[str, Any]:
    if not OPENWEATHER:
        return {"error": "missing OPENWEATHER_API_KEY"}
    key = f"wx:{lat}:{lon}:{q}:{units}"
    def _call():
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"appid": OPENWEATHER, "units": units, "lang": "th"}
        if lat is not None and lon is not None:
            params.update({"lat": lat, "lon": lon})
        elif q:
            params.update({"q": q})
        js = _fetch_json(url, params=params)
        main = js.get("main", {})
        wx = js.get("weather", [{}])[0]
        wind = js.get("wind", {})
        return {
            "name": js.get("name") or q,
            "temp": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "desc": wx.get("description"),
            "wind_kmh": (float(wind.get("speed", 0)) * 3.6) if wind else None,
            "source": "openweather",
        }
    # อากาศเปลี่ยนช้ากว่า: TTL ~ 10 นาที
    return _cache_get_or(key, ttl=600, fn=_call)

# Crypto (เช่น BTC, ETH)
def get_crypto_price(symbol: str, vs: str = "USD") -> Dict[str, Any]:
    sym = symbol.lower()
    key = f"cg:{sym}:{vs.lower()}"
    def _call():
        url = f"{COINGECKO_BASE}/simple/price"
        js = _fetch_json(url, params={"ids": sym, "vs_currencies": vs.lower()})
        price = js.get(sym, {}).get(vs.lower())
        return {"symbol": symbol.upper(), "vs": vs.upper(), "price": float(price) if price is not None else None, "source": "coingecko"}
    # คริปโตเคลื่อนไหวไว: TTL 10s
    return _cache_get_or(key, ttl=10, fn=_call)

# Stocks (แบบ quote ปัจจุบัน)
def get_stock_quote(symbol: str) -> Dict[str, Any]:
    key = f"st:{symbol.upper()}"
    def _call():
        # Primary: Finnhub
        if FINNHUB_KEY:
            url = "https://finnhub.io/api/v1/quote"
            js = _fetch_json(url, params={"symbol": symbol.upper(), "token": FINNHUB_KEY})
            if "c" in js:
                return {"symbol": symbol.upper(), "price": float(js["c"]), "open": js.get("o"), "high": js.get("h"), "low": js.get("l"), "source": "finnhub"}
        # Fallback: Yahoo (unofficial quick endpoint)
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        js = _fetch_json(url, params={"symbols": symbol.upper()})
        rs = js.get("quoteResponse", {}).get("result", [])
        if rs:
            q = rs[0]
            return {"symbol": symbol.upper(), "price": q.get("regularMarketPrice"), "open": q.get("regularMarketOpen"), "high": q.get("regularMarketDayHigh"), "low": q.get("regularMarketDayLow"), "source": "yahoo"}
        return {"symbol": symbol.upper(), "price": None, "source": "unknown"}
    # TTL 30s ช่วงตลาดเปิด
    return _cache_get_or(key, ttl=30, fn=_call)

# Gold (ราคาทองโลกหรือ spot) – ถ้ามี key ใช้, ไม่มีก็ None (คุณอาจต่อแหล่งไทยภายหลัง)
def get_gold_price_spot() -> Dict[str, Any]:
    if not GOLDAPI_KEY:
        return {"price": None, "currency": "USD", "source": "goldapi (no key)"}
    key = "gold:spot"
    def _call():
        url = "https://www.goldapi.io/api/XAU/USD"
        js = _fetch_json(url, headers={"x-access-token": GOLDAPI_KEY})
        return {"price": js.get("price"), "currency": "USD", "source": "goldapi"}
    # ทองไม่ได้วิ่งวินาทีต่อวินาที: TTL 60s
    return _cache_get_or(key, ttl=60, fn=_call)

# น้ำมันในไทย (โดยมากอัปเดตรายวัน) — placeholder ให้คุณต่อแหล่งข้อมูลจริงที่ใช้อยู่
def get_oil_price_th() -> Dict[str, Any]:
    # ตรงนี้คุณสามารถต่อ API/สครัปที่คุณใช้อยู่แล้ว แล้วคืน dict เดียวกันได้เลย
    key = "oil:th"
    def _call():
        return {"source": "manual-or-internal", "note": "ต่อ API ราคาน้ำมันไทยที่คุณใช้ แล้วใส่ TTL ยาวขึ้นได้เลย"}
    # TTL ยาว ๆ 12 ชั่วโมง
    return _cache_get_or(key, ttl=43200, fn=_call)
