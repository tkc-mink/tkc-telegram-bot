# utils/lottery_utils.py
# -*- coding: utf-8 -*-
"""
Utility for fetching the latest lottery results using a reliable search tool.
This replaces the previous, fragile web scraping method.
"""
from __future__ import annotations
from typing import Optional

# ✅ เปลี่ยนมาใช้เครื่องมือภายในที่เสถียรกว่า
try:
    from internal_tools import Google Search
except ImportError:
    print("WARNING: 'internal_tools.Google Search' not found. Using mock data for lottery.")
    class MockLotteryResult:
        def __init__(self, snippet): self.snippet = snippet
    class MockSearchResults:
        def __init__(self, results): self.results = results
    def search_mock(queries=None):
        return [MockSearchResults([MockLotteryResult(
            "ผลสลากกินแบ่งรัฐบาล งวดวันที่ 1 สิงหาคม 2568 รางวัลที่ 1: 123456, เลขท้าย 2 ตัว: 78"
        )])]
    Google Search = type("GoogleSearch", (), {"search": staticmethod(search_mock)})


def get_lottery_result() -> str:
    """
    Fetches the latest official lottery results using a reliable Google search.
    """
    print("[Lottery_Utils] Fetching latest lottery results...")
    # สร้างคำค้นหาที่เจาะจงและเป็นกลาง
    query = "ผลสลากกินแบ่งรัฐบาลล่าสุด"

    try:
        search_results = Google Search(queries=[query])

        if search_results and search_results[0].results and search_results[0].results[0].snippet:
            # ผลลัพธ์จาก Google Search มักจะมีข้อมูลสรุปที่ชัดเจน
            lottery_data = search_results[0].results[0].snippet

            # จัดรูปแบบข้อความให้สวยงามและอ่านง่าย
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
