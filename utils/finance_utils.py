# utils/finance_utils.py
# -*- coding: utf-8 -*-
"""
Central utility for fetching financial data using web scraping.
This is Plan B to bypass the persistent SyntaxError.
"""
from __future__ import annotations
from typing import Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

def _scrape_google_finance(query: str) -> Optional[str]:
    """Helper function to scrape Google search results for financial data."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    # Encode the query to handle special characters
    encoded_query = quote(query)
    url = f"https://www.google.com/search?q={encoded_query}&hl=th"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # This is a common class used by Google for direct answers.
        price_div = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
        
        if price_div:
            return price_div.text
        # Fallback for different structures
        price_span = soup.find('span', class_='IsqA6b')
        if price_span:
            return price_span.text
            
        return None
    except Exception as e:
        print(f"[Finance_Utils] Scraping error for query '{query}': {e}")
        return None

def get_stock_info_from_google(symbol: str) -> Optional[str]:
    """Fetches stock info using the scraping helper."""
    print(f"[Finance_Utils] Scraping stock symbol: {symbol}")
    result = _scrape_google_finance(f"stock price {symbol}")
    if result:
        return (f"📈 **ข้อมูลหุ้น {symbol.upper()}**\n---------------------------------\n{result}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google*")
    return f"ไม่พบข้อมูลหุ้น {symbol.upper()}"

def get_crypto_price_from_google(symbol: str) -> Optional[str]:
    """Fetches crypto info using the scraping helper."""
    if "-" not in symbol: symbol = f"{symbol}-USD"
    print(f"[Finance_Utils] Scraping crypto symbol: {symbol}")
    result = _scrape_google_finance(f"crypto price {symbol}")
    if result:
        return (f"💸 **ข้อมูลเหรียญ {symbol.split('-')[0].upper()}**\n---------------------------------\n{result}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google*")
    return f"ไม่พบข้อมูลเหรียญ {symbol.split('-')[0].upper()}"

def get_oil_price_from_google() -> Optional[str]:
    """Fetches oil price info using the scraping helper."""
    print("[Finance_Utils] Scraping oil prices")
    result = _scrape_google_finance("oil price wti brent")
    if result:
        return (f"🛢️ **ราคาน้ำมันดิบ (ล่าสุด)**\n---------------------------------\n{result}\n---------------------------------\n*ข้อมูลล่าสุดจาก Google*")
    return "ไม่พบข้อมูลราคาน้ำมัน"
