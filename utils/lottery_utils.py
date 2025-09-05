# utils/lottery_utils.py
# -*- coding: utf-8 -*-
"""
Thai Lottery (GLO) Result Utility — resilient, multi-provider
- Provider ลำดับความสำคัญ: DIRECT API -> internal_tools.google_search -> MOCK
- แยก/จับข้อมูลด้วย regex ให้ได้: รางวัลที่ 1, เลขหน้า 3 ตัว, เลขท้าย 3 ตัว, เลขท้าย 2 ตัว, วันที่งวด (ถ้าเจอ)
- เหมาะกับ Telegram bot (ข้อความ plain ไม่พัง Markdown)
- ตั้งค่าได้ด้วย ENV:
    LOTTERY_PROVIDER   = "auto" | "api" | "google" | "mock"   (default: auto)
    LOTTERY_HTTP_TO    = seconds (default: 8)
    LOTTERY_API_URL    = override URL ของผู้ให้บริการ API (default: https://lotto.api.rayriffy.com/latest)
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
import re
import json
import datetime

# -------------------- Provider: API (optional) --------------------
try:
    import requests  # ใช้เฉพาะเมื่อ provider = api/auto
except Exception:
    requests = None  # จะ fallback ไป provider อื่น

# -------------------- Provider: internal google_search --------------------
# Corrected import name from "Google Search" -> "google_search"
try:
    from internal_tools import google_search  # ต้องมี method: search(queries=[...]) -> [SearchResults]
except Exception:
    google_search = None

# -------------------- Config --------------------
LOTTERY_PROVIDER = (os.getenv("LOTTERY_PROVIDER") or "auto").strip().lower()
LOTTERY_HTTP_TO = int(os.getenv("LOTTERY_HTTP_TO", "8"))
DEFAULT_API_URL = os.getenv("LOTTERY_API_URL", "https://lotto.api.rayriffy.com/latest")

# -------------------- Regex patterns --------------------
# พยายามรองรับทั้งไทย/อังกฤษจากผลค้นหา/เว็บข่าว
RE_DATE = re.compile(
    r"(?:งวดวันที่|งวดประจำ|draw(?: date)?:?)\s*([0-9]{1,2}\s*(?:ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.\s?ค\.|ส\.\s?ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม|January|February|March|April|May|June|July|August|September|October|November|December)\s*[0-9]{4})",
    re.IGNORECASE,
)

RE_FIRST = re.compile(r"(?:รางวัลที่\s*1|First\s*prize)[:\s]*([0-9]{6})", re.IGNORECASE)
RE_LAST2 = re.compile(r"(?:เลขท้าย\s*2\s*ตัว|2-?digit(?:\sprize)?)[:\s]*([0-9]{2})", re.IGNORECASE)

# อาจเจอ 2 เลข แยกด้วยช่องว่าง/คอมมา/ขีด
RE_FRONT3 = re.compile(r"(?:เลขหน้า\s*3\s*ตัว|front\s*3-?digits?)[:\s]*([0-9]{3})(?:\D+([0-9]{3}))?", re.IGNORECASE)
RE_LAST3  = re.compile(r"(?:เลขท้าย\s*3\s*ตัว|last\s*3-?digits?)[:\s]*([0-9]{3})(?:\D+([0-9]{3}))?", re.IGNORECASE)

# -------------------- Core helpers --------------------
def _fmt_human(result: Dict[str, Any]) -> str:
    """จัดข้อความเป็นบล็อกอ่านง่าย (plain text ปลอดภัยกับ Telegram Markdown)"""
    lines: List[str] = []
    date_txt = result.get("date") or "งวดล่าสุด"
    lines.append(f"ผลสลากกินแบ่งรัฐบาล ({date_txt})")
    lines.append("-" * 36)

    if result.get("first_prize"):
        lines.append(f"รางวัลที่ 1       : {result['first_prize']}")
    if result.get("front3"):
        fronts = " ".join(result["front3"])
        lines.append(f"เลขหน้า 3 ตัว    : {fronts}")
    if result.get("last3"):
        lasts = " ".join(result["last3"])
        lines.append(f"เลขท้าย 3 ตัว     : {lasts}")
    if result.get("last2"):
        lines.append(f"เลขท้าย 2 ตัว     : {result['last2']}")

    lines.append("-" * 36)
    lines.append("ขอให้โชคดีครับ ✨")
    return "\n".join(lines)

def _empty_result() -> Dict[str, Any]:
    return {"date": None, "first_prize": None, "front3": [], "last3": [], "last2": None}

def _merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """รวมผลจากหลายแหล่งแบบอนุรักษ์ข้อมูลที่มีอยู่แล้ว"""
    out = dict(a)
    for k, v in b.items():
        if k in {"front3", "last3"}:
            exist = set(out.get(k) or [])
            for n in (v or []):
                if n and n not in exist:
                    out.setdefault(k, []).append(n)
        else:
            if v and not out.get(k):
                out[k] = v
    return out

# -------------------- Provider: API --------------------
def _fetch_from_api() -> Optional[Dict[str, Any]]:
    """
    พยายามเรียก API ตรง (ค่า default ใช้บริการยอดนิยมในไทย)
    โครงสร้าง JSON แหล่งต่าง ๆ อาจต่างกัน โค้ดนี้พยายาม parse แบบยืดหยุ่น
    """
    if not requests:
        return None
    url = DEFAULT_API_URL
    try:
        resp = requests.get(url, timeout=LOTTERY_HTTP_TO)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[lottery] API fetch error: {e}")
        return None

    # พยายาม map ให้เป็นรูปเดียวกัน
    result = _empty_result()

    # เคสที่ API มี field 'response' ซ้อน
    payload = data.get("response") if isinstance(data, dict) and "response" in data else data

    # เดาว่ามี date
    for key in ("date", "drawDate", "issuedate"):
        val = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(val, str) and len(val) >= 6:
            result["date"] = val
            break

    # โครงสร้างแบบ 'prizes': [{name, numbers/list/...}]
    prizes = payload.get("prizes") if isinstance(payload, dict) else None
    if isinstance(prizes, list):
        for p in prizes:
            name = (p.get("name") or "").strip()
            # ตัวเลขอาจอยู่ใน keys ต่างกัน เช่น "number"/"numbers"/"raw"/"rewardNumbers"
            nums = None
            for key in ("number", "numbers", "raw", "rewardNumbers"):
                if key in p:
                    nums = p[key]
                    break
            if nums is None:
                continue
            if isinstance(nums, list):
                s = [str(x).strip() for x in nums if str(x).strip()]
            else:
                s = [str(nums).strip()]

            if re.search(r"รางวัลที่\s*1|first", name, re.IGNORECASE):
                # คาดหวังเป็นเลข 6 หลัก
                for x in s:
                    if re.fullmatch(r"\d{6}", x):
                        result["first_prize"] = x
                        break
            elif re.search(r"เลขหน้า\s*3|front\s*3", name, re.IGNORECASE):
                for x in s:
                    if re.fullmatch(r"\d{3}", x) and x not in result["front3"]:
                        result["front3"].append(x)
            elif re.search(r"เลขท้าย\s*3|last\s*3", name, re.IGNORECASE):
                for x in s:
                    if re.fullmatch(r"\d{3}", x) and x not in result["last3"]:
                        result["last3"].append(x)
            elif re.search(r"เลขท้าย\s*2|2\s*ตัว|last\s*2|two\s*digits", name, re.IGNORECASE):
                for x in s:
                    if re.fullmatch(r"\d{2}", x):
                        result["last2"] = x
                        break

    # โครงสร้างแบบแยก key โดยตรง (รองรับบาง API)
    if not result["first_prize"]:
        for k in ("first", "firstPrize", "first_prize"):
            v = payload.get(k) if isinstance(payload, dict) else None
            if isinstance(v, (str, int)) and re.fullmatch(r"\d{6}", str(v)):
                result["first_prize"] = str(v)
                break

    if not result["last2"]:
        for k in ("last2", "lastTwo", "twoDigits"):
            v = payload.get(k) if isinstance(payload, dict) else None
            if isinstance(v, (str, int)) and re.fullmatch(r"\d{2}", str(v)):
                result["last2"] = str(v)
                break

    for kind, keys in (("front3", ("front3", "frontThree", "frontThreeDigits")),
                       ("last3",  ("last3", "lastThree", "lastThreeDigits"))):
        if not result[kind] and isinstance(payload, dict):
            v = payload.get(keys[0]) or payload.get(keys[1]) or payload.get(keys[2], None)
            if isinstance(v, list):
                for x in v:
                    x = str(x).strip()
                    if re.fullmatch(r"\d{3}", x) and x not in result[kind]:
                        result[kind].append(x)

    # ถ้าไม่มีอะไรเลย ให้ถือว่า API ไม่ใช้ได้
    has_any = result["first_prize"] or result["last2"] or result["front3"] or result["last3"]
    return result if has_any else None

# -------------------- Provider: Google Search (internal) --------------------
def _fetch_from_google() -> Optional[Dict[str, Any]]:
    """
    ใช้ internal_tools.google_search เพื่อดึง snippet แล้ว regex จับเลข
    """
    if not google_search:
        return None

    try:
        # ใช้คำค้นไทยตรง ๆ จะให้ผลดีกว่า
        queries = ["ผลสลากกินแบ่งรัฐบาลล่าสุด", "ผลหวยรัฐบาล งวดล่าสุด"]
        srch = google_search.search(queries=queries)  # คาดหวัง list ของกลุ่มผลลัพธ์
    except Exception as e:
        print(f"[lottery] google_search error: {e}")
        return None

    res_all = _empty_result()
    try:
        # เดินทุกชุด/ทุก result เก็บ text ทั้งหมดมารวมแล้วจับ regex
        texts: List[str] = []
        if srch:
            for group in srch:
                for item in getattr(group, "results", []) or []:
                    snippet = getattr(item, "snippet", "") or ""
                    if snippet:
                        texts.append(snippet)

        if not texts:
            return None

        merged_text = "\n".join(texts)

        r = _empty_result()
        # date
        m = RE_DATE.search(merged_text)
        if m:
            r["date"] = m.group(1).strip()

        # first prize
        m = RE_FIRST.search(merged_text)
        if m:
            r["first_prize"] = m.group(1)

        # last 2
        m = RE_LAST2.search(merged_text)
        if m:
            r["last2"] = m.group(1)

        # front3 (อาจมี 1–2 เบอร์)
        m = RE_FRONT3.search(merged_text)
        if m:
            vs = [m.group(1), m.group(2)]
            r["front3"] = [x for x in vs if x and re.fullmatch(r"\d{3}", x)]

        # last3 (อาจมี 1–2 เบอร์)
        m = RE_LAST3.search(merged_text)
        if m:
            vs = [m.group(1), m.group(2)]
            r["last3"] = [x for x in vs if x and re.fullmatch(r"\d{3}", x)]

        # ต้องมีอย่างน้อย 1 ฟิลด์จึงถือว่าพอใช้
        has_any = r["first_prize"] or r["last2"] or r["front3"] or r["last3"]
        if not has_any:
            return None

        res_all = _merge(res_all, r)
        return res_all
    except Exception as e:
        print(f"[lottery] google parse error: {e}")
        return None

# -------------------- Provider: Mock (offline dev) --------------------
def _fetch_from_mock() -> Dict[str, Any]:
    # ใส่ตัวเลขตัวอย่าง (ปลอดภัยสำหรับ dev/test)
    today = datetime.date.today().isoformat()
    return {
        "date": f"ตัวอย่าง {today}",
        "first_prize": "123456",
        "front3": ["123", "456"],
        "last3": ["789", "012"],
        "last2": "99",
    }

# -------------------- Public API --------------------
def get_lottery_result() -> str:
    """
    คืนค่าข้อความผลสลาก (งวดล่าสุด) ในรูปแบบพร้อมส่ง Telegram
    ลำดับ provider:
        1) ถ้า LOTTERY_PROVIDER=api หรือ auto -> พยายามเรียก API ก่อน
        2) ถ้า LOTTERY_PROVIDER=google หรือ auto -> ใช้ internal google_search
        3) mock
    """
    print("[Lottery] Fetching latest lottery results ...")

    provider = LOTTERY_PROVIDER or "auto"
    final: Dict[str, Any] = _empty_result()

    tried = []

    # 1) API
    if provider in ("api", "auto"):
        tried.append("api")
        api_res = _fetch_from_api()
        if api_res:
            final = _merge(final, api_res)

    # 2) google_search
    if provider in ("google", "auto") and (not final["first_prize"] or not final["last2"]):
        tried.append("google")
        g_res = _fetch_from_google()
        if g_res:
            final = _merge(final, g_res)

    # 3) mock (ถ้ายังไม่มีอะไรเลย)
    if not (final["first_prize"] or final["last2"] or final["front3"] or final["last3"]):
        tried.append("mock")
        final = _fetch_from_mock()

    print(f"[Lottery] tried providers: {tried}")

    # สุดท้าย: format เป็นข้อความ
    return _fmt_human(final)

# -------------------- Optional: raw dict for other handlers --------------------
def get_lottery_result_raw() -> Dict[str, Any]:
    """
    ถ้าต้องการผลแบบโครงสร้าง (สำหรับ handler ที่อยากจัดหน้าพิเศษ)
    """
    provider = LOTTERY_PROVIDER or "auto"
    final: Dict[str, Any] = _empty_result()

    if provider in ("api", "auto"):
        api_res = _fetch_from_api()
        if api_res:
            final = _merge(final, api_res)

    if provider in ("google", "auto") and (not final["first_prize"] or not final["last2"]):
        g_res = _fetch_from_google()
        if g_res:
            final = _merge(final, g_res)

    if not (final["first_prize"] or final["last2"] or final["front3"] or final["last3"]):
        final = _fetch_from_mock()

    return final

# -------------------- CLI quick test --------------------
if __name__ == "__main__":
    print(get_lottery_result())
