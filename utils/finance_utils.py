# utils/finance_utils.py
# -*- coding: utf-8 -*-
"""
Central utility for fetching all financial data (stocks, crypto, oil)
using a reliable, internal Google Search tool. This is the master version. (Syntax Fixed)
"""
from __future__ import annotations
from typing import Dict, Optional

# ✅ แก้ไขชื่อ "Google Search" เป็น "Google Search" ที่ถูกต้อง
try:
    from internal_tools import Google Search
except ImportError:
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data for finance utils.")
    class MockSearchResult:
        def __init__(self, snippet="", title=""): self.snippet, self.title = snippet, title
    class MockSearchResults:
        def __init__(self, results): self.results = results
    def search_mock(queries=None):
        query = queries[0] if queries else ""
        if "stock price" in query: return [MockSearchResults([MockSearchResult(snippet="Price: 34.50 THB, Change: +0.25 (0.73%)", title="PTT PCL (PTT.BK)")])]
        if "crypto price" in query: return [MockSearchResults([MockSearchResult(snippet="Price: $65,123.45 USD, Change: -$1,234.56 (-1.86%)", title="Bitcoin (BTC)")])]
        if "oil price" in query: return [MockSearchResults([MockSearchResult(snippet="WTI Crude: $80.50/bbl | Brent Crude: $85.00/bbl")])]
        return [MockSearchResults([])]
    Google Search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_stock_info_from_google(symbol: str) -> Optional[str]:
    query = f"stock price {symbol} site:google.com/finance"
    try:
        results = Google Search(queries=[query])
        if results and results[0].results:
            res, name = results[0].results[0], res.title.split("(")[0].strip() if res.title else symbol
            return (f"📈 **ข้อมูลหุ้น {name} ({symbol})**\n---------------------------------\n{res.snippet}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google Finance*")
        return None
    except Exception as e:
        print(f"[Finance_Utils] An error occurred while fetching stock info for {symbol}: {e}")
        return None

def get_crypto_price_from_google(symbol: str) -> Optional[str]:
    if "-" not in symbol: symbol = f"{symbol}-USD"
    query = f"crypto price {symbol} site:google.com/finance"
    try:
        results = Google Search(queries=[query])
        if results and results[0].results:
            res, name = results[0].results[0], res.title.split("(")[0].strip() if res.title else symbol.split("-")[0]
            return (f"💸 **ข้อมูลเหรียญ {name} ({symbol.split('-')[0]})**\n---------------------------------\n{res.snippet}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google Finance*")
        return None
    except Exception as e:
        print(f"[Finance_Utils] Error fetching crypto info for {symbol}: {e}")
        return None

def get_oil_price_from_google() -> Optional[str]:
    query = "oil price WTI brent site:google.com/finance"
    try:
        results = Google Search(queries=[query])
        if results and results[0].results:
            return (f"🛢️ **ราคาน้ำมันดิบ (ล่าสุด)**\n---------------------------------\n{results[0].results[0].snippet}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google Finance*")
        return None
    except Exception as e:
        print(f"[Finance_Utils] Error fetching oil prices: {e}")
        return None
