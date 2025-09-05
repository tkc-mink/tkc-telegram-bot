# utils/finance_utils.py
# -*- coding: utf-8 -*-
"""
Central utility for fetching financial data (hardened, drop-in)
Priority:
  1) Yahoo Finance quote JSON (no key)
  2) CoinGecko (crypto fallback, no key)
  3) Google SERP scrape (last-resort for compatibility)

ENV (optional):
  FIN_TIMEOUT_SEC=10
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
import os
import time
import datetime as _dt
import requests
from requests.adapters import HTTPAdapter
try:
    # urllib3 <2/==2 friendly import
    from urllib3.util.retry import Retry  # type: ignore
except Exception:
    Retry = None

from bs4 import BeautifulSoup
from urllib.parse import quote

FIN_TIMEOUT = int(os.getenv("FIN_TIMEOUT_SEC", "10"))

# -------------------- HTTP session with retry --------------------
def _build_session(timeout: int = FIN_TIMEOUT, retries: int = 2, backoff: float = 0.5) -> requests.Session:
    s = requests.Session()
    if Retry is not None:
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            backoff_factor=backoff,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
    _orig = s.request
    def _req(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return _orig(method, url, **kwargs)
    s.request = _req  # type: ignore
    return s

_session = _build_session()

# -------------------- Formatting helpers --------------------
def _fmt_num(n: Optional[float], decimals: int = 2) -> str:
    if n is None:
        return "-"
    try:
        return f"{float(n):,.{decimals}f}"
    except Exception:
        return str(n)

def _fmt_change(chg: Optional[float], chg_pct: Optional[float]) -> str:
    if chg is None and chg_pct is None:
        return ""
    parts = []
    if chg is not None:
        parts.append(_fmt_num(chg))
    if chg_pct is not None:
        sign = "+" if chg_pct >= 0 else ""
        parts.append(f"{sign}{_fmt_num(chg_pct, 2)}%")
    s = " / ".join(parts)
    if chg is not None:
        sign = "🔺" if chg >= 0 else "🔻"
    else:
        sign = "🔺" if (chg_pct or 0) >= 0 else "🔻"
    return f"{sign} {s}"

def _fmt_epoch_ms(ms: Optional[int]) -> str:
    try:
        if not ms:
            return "-"
        dt = _dt.datetime.fromtimestamp(ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"

def _bold(s: str) -> str:
    # ใช้ **...** ให้เข้ากับข้อความเดิมของโปรเจกต์
    return f"**{s}**"

# -------------------- Yahoo Finance quote (primary) --------------------
def _yahoo_quote(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Return mapping symbol -> quote dict using Yahoo Finance JSON API
    """
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": ",".join(symbols)}
        r = _session.get(url, params=params)
        if r.status_code != 200:
            return {}
        data = r.json()
        res = {}
        items = (data or {}).get("quoteResponse", {}).get("result", []) or []
        for it in items:
            sym = it.get("symbol")
            if sym:
                res[sym.upper()] = it
        return res
    except Exception as e:
        print(f"[Finance_Utils] Yahoo quote error: {e}")
        return {}

# -------------------- CoinGecko (crypto fallback) --------------------
_CG_ID_MAP = {
    "BTC": "bitcoin", "XBT": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "TON": "the-open-network",
    "ARB": "arbitrum",
    "MATIC": "polygon",
}

def _coingecko_simple(id_: str, vs: str = "usd") -> Optional[float]:
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": id_, "vs_currencies": vs}
        r = _session.get(url, params=params)
        if r.status_code != 200:
            return None
        data = r.json()
        return (data.get(id_) or {}).get(vs)
    except Exception as e:
        print(f"[Finance_Utils] CoinGecko error: {e}")
        return None

# -------------------- Legacy Google scrape (last resort) --------------------
def _scrape_google_finance(query: str) -> Optional[str]:
    """Helper function to scrape Google search results for financial data (last resort)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        )
    }
    encoded_query = quote(query)
    url = f"https://www.google.com/search?q={encoded_query}&hl=th"
    try:
        resp = _session.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Common direct-answer containers (fragile)
        price_div = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
        if price_div:
            return price_div.text

        price_span = soup.find('span', class_='IsqA6b')
        if price_span:
            return price_span.text
        return None
    except Exception as e:
        print(f"[Finance_Utils] Scraping error for query '{query}': {e}")
        return None

# -------------------- Public APIs --------------------
def get_stock_info_from_google(symbol: str) -> str:
    """
    Fetch stock info (hardened):
      - Try Yahoo Finance quote
      - Fallback Google scrape (last resort)
    """
    sym = symbol.strip().upper()
    print(f"[Finance_Utils] Fetching stock: {sym}")

    # 1) Yahoo Finance
    quotes = _yahoo_quote([sym])
    q = quotes.get(sym)
    if q:
        name = q.get("longName") or q.get("shortName") or sym
        price = q.get("regularMarketPrice")
        currency = q.get("currency") or ""
        chg = q.get("regularMarketChange")
        pct = q.get("regularMarketChangePercent")
        tms = q.get("regularMarketTime") or q.get("postMarketTime") or 0
        updated = _fmt_epoch_ms(tms * 1000 if tms < 10_000_000_000 else tms)

        body = [
            f"{_bold(f'ข้อมูลหุ้น {name} ({sym})')}",
            "---------------------------------",
            f"ราคา: {_fmt_num(price)} {currency} {_fmt_change(chg, pct)}",
            f"อัปเดตล่าสุด: {updated}",
            "---------------------------------",
            "*ที่มา: Yahoo Finance*",
        ]
        return "\n".join(body)

    # 2) Google scrape (last resort)
    result = _scrape_google_finance(f"stock price {sym}")
    if result:
        return (
            f"📈 {_bold(f'ข้อมูลหุ้น {sym}')}\n"
            "---------------------------------\n"
            f"{result}\n"
            "---------------------------------\n"
            "*ข้อมูลล่าสุดจาก Google*"
        )
    return f"ไม่พบข้อมูลหุ้น {sym}"

def get_crypto_price_from_google(symbol: str) -> str:
    """
    Fetch crypto price:
      - Try Yahoo Finance (e.g., BTC-USD). If user passed 'BTC' -> assume USD.
      - Fallback CoinGecko (USD).
      - Final fallback Google scrape.
    """
    raw = symbol.strip().upper()
    base, vs = (raw.split("-", 1) + ["USD"])[:2] if "-" in raw else (raw, "USD")
    y_sym = f"{base}-{vs}"

    print(f"[Finance_Utils] Fetching crypto: {y_sym}")

    # 1) Yahoo Finance
    q = _yahoo_quote([y_sym]).get(y_sym)
    if q:
        name = q.get("shortName") or base
        price = q.get("regularMarketPrice")
        currency = q.get("currency") or vs
        chg = q.get("regularMarketChange")
        pct = q.get("regularMarketChangePercent")
        tms = q.get("regularMarketTime") or 0
        updated = _fmt_epoch_ms(tms * 1000 if tms < 10_000_000_000 else tms)
        body = [
            f"💸 {_bold(f'ข้อมูลเหรียญ {name} ({base})')}",
            "---------------------------------",
            f"ราคา: {_fmt_num(price)} {currency} {_fmt_change(chg, pct)}",
            f"อัปเดตล่าสุด: {updated}",
            "---------------------------------",
            "*ที่มา: Yahoo Finance*",
        ]
        return "\n".join(body)

    # 2) CoinGecko fallback
    cg_id = _CG_ID_MAP.get(base) or base.lower()
    cg_price = _coingecko_simple(cg_id, vs.lower())
    if cg_price is not None:
        body = [
            f"💸 {_bold(f'ข้อมูลเหรียญ {base}')}",
            "---------------------------------",
            f"ราคา: {_fmt_num(cg_price)} {vs.upper()}",
            "---------------------------------",
            "*ที่มา: CoinGecko*",
        ]
        return "\n".join(body)

    # 3) Google scrape
    g = _scrape_google_finance(f"crypto price {base}-{vs}")
    if g:
        return (
            f"💸 {_bold(f'ข้อมูลเหรียญ {base}')}\n"
            "---------------------------------\n"
            f"{g}\n"
            "---------------------------------\n"
            "*ข้อมูลล่าสุดจาก Google*"
        )
    return f"ไม่พบข้อมูลเหรียญ {base}"

def get_oil_price_from_google() -> str:
    """
    Fetch oil prices:
      - Use Yahoo Finance futures: WTI(CL=F), Brent(BZ=F)
      - Fallback Google scrape (generic)
    """
    print("[Finance_Utils] Fetching oil prices (CL=F, BZ=F)")
    quotes = _yahoo_quote(["CL=F", "BZ=F"])  # WTI & Brent futures
    cl, bz = quotes.get("CL=F"), quotes.get("BZ=F")

    if cl or bz:
        lines = ["🛢️ " + _bold("ราคาน้ำมันดิบ (ล่าสุด)"), "---------------------------------"]
        if cl:
            lines.append(
                f"WTI (CL=F): {_fmt_num(cl.get('regularMarketPrice'))} {cl.get('currency','')}"
                f" {_fmt_change(cl.get('regularMarketChange'), cl.get('regularMarketChangePercent'))}"
            )
        if bz:
            lines.append(
                f"Brent (BZ=F): {_fmt_num(bz.get('regularMarketPrice'))} {bz.get('currency','')}"
                f" {_fmt_change(bz.get('regularMarketChange'), bz.get('regularMarketChangePercent'))}"
            )
        # choose the freshest timestamp available
        tms = max(
            (cl.get("regularMarketTime") or 0) if cl else 0,
            (bz.get("regularMarketTime") or 0) if bz else 0,
        )
        updated = _fmt_epoch_ms(tms * 1000 if tms and tms < 10_000_000_000 else tms)
        lines += ["อัปเดตล่าสุด: " + updated, "---------------------------------", "*ที่มา: Yahoo Finance*"]
        return "\n".join(lines)

    # Fallback: Google scrape generic
    g = _scrape_google_finance("oil price WTI Brent")
    if g:
        return (
            "🛢️ " + _bold("ราคาน้ำมันดิบ (ล่าสุด)") + "\n"
            "---------------------------------\n"
            f"{g}\n"
            "---------------------------------\n"
            "*ข้อมูลล่าสุดจาก Google*"
        )
    return "ไม่พบข้อมูลราคาน้ำมัน"
