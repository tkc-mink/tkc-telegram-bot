# utils/lottery_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching the latest lottery results using a reliable search tool.
This version corrects a syntax error in the import statement.
"""
from __future__ import annotations

# Corrected the import from "Google Search" to "google_search"
try:
    from internal_tools import google_search
except ImportError:
    print("WARNING: 'internal_tools.google_search' not found. Using mock data for lottery.")
    class MockLotteryResult:
        def __init__(self, snippet):
            self.snippet = snippet
    class MockSearchResults:
        def __init__(self, results):
            self.results = results
    def search_mock(queries=None):
        return [MockSearchResults([MockLotteryResult(
            "Lottery results for August 28, 2025: First prize: 123456, 2-digit prize: 78"
        )])]
    google_search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_lottery_result() -> str:
    """
    Fetches the latest official lottery results using a reliable Google search.
    """
    print("[Lottery_Utils] Fetching latest lottery results...")
    query = "ผลสลากกินแบ่งรัฐบาลล่าสุด"

    try:
        # Use the corrected 'google_search' object
        search_results = google_search.search(queries=[query])

        if search_results and search_results[0].results and search_results[0].results[0].snippet:
            lottery_data = search_results[0].results[0].snippet

            message = (
                f"🎉 **ผลสลากกินแบ่งรัฐบาล (งวดล่าสุด)**\n"
                f"------------------------------------\n"
                f"{lottery_data}\n"
                f"------------------------------------\n"
                f"*ขอให้โชคดีนะครับ!*"
            )
            return message
        else:
            print("[Lottery_Utils] No lottery results found.")
            return "❌ ขออภัยครับ ไม่พบข้อมูลผลสลากในขณะนี้"

    except Exception as e:
        print(f"[Lottery_Utils] An error occurred while fetching lottery results: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดทางเทคนิคในการดึงข้อมูลผลสลาก"
