import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple

# ------------------- HTTP session with retry -------------------
from requests.adapters import HTTPAdapter
try:
    # urllib3 <2 / =2 friendly import
    from urllib3.util.retry import Retry  # type: ignore
except Exception:
    Retry = None

def _build_session(timeout: int = 10, retries: int = 2, backoff: float = 0.5) -> requests.Session:
    s = requests.Session()
    if Retry is not None:
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
    # default timeout wrapper
    orig_req = s.request
    def _req(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return orig_req(method, url, **kwargs)
    s.request = _req  # type: ignore
    return s

# ------------------- Text helpers -------------------
_TH2AR = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

def _clean_num(txt: str) -> str:
    """
    คืนสตริงตัวเลขราคาแบบพร้อมคอมมา เช่น '38,100.00'
    รับทั้งเลขไทย/อารบิก และตัดคำ/หน่วยที่ไม่เกี่ยวออก
    """
    if not txt:
        return ""
    t = txt.strip().translate(_TH2AR)
    # เก็บเฉพาะตัวเลข จุด คอมมา
    t = re.sub(r"[^0-9\.,]", "", t)
    # ถ้ามีจุดมากกว่า 1 ให้ตัดทิ้งทั้งหมด (ป้องกัน parse แปลก ๆ)
    if t.count(".") > 1:
        t = t.replace(".", "")
    # จัดรูปแบบคอมมาใหม่เมื่อเป็นตัวเลขล้วน
    try:
        # ถ้ามีจุด -> ทศนิยม
        if "." in t:
            val = float(t.replace(",", ""))
            return f"{val:,.2f}"
        else:
            val = int(float(t.replace(",", "")))
            return f"{val:,}"
    except Exception:
        return t

def _find_updated_text(soup: BeautifulSoup) -> Optional[str]:
    # พยายามหา "อัพเดทล่าสุด", "ปรับครั้งที่", "ครั้งที่", "Last update"
    text = soup.get_text(" ", strip=True)
    m = re.search(r"(อัปเดต|อัพเดท|ปรับ(?:ครั้งที่)?|Last\s*update).*?(\d{1,2}[:.]\d{2}).*?(น\.|AM|PM)?", text, re.IGNORECASE)
    if m:
        return m.group(0)
    # บางทีมีรูปแบบ "ประจำวันที่ dd/mm/yyyy เวลา hh:mm น."
    m = re.search(r"(ประจำวัน|ประจำวันที่|งวดวันที่).*?\d{1,2}\/\d{1,2}\/\d{2,4}.*?\d{1,2}[:.]\d{2}", text)
    if m:
        return m.group(0)
    return None

def _parse_goldtraders(html: str) -> Tuple[Optional[str], Dict[str, str]]:
    """
    คืน (updated_text, prices_dict)
    prices_dict keys: bar_buy, bar_sell, ornament_buy, ornament_sell
    """
    soup = BeautifulSoup(html, "html.parser")
    updated = _find_updated_text(soup)

    prices = {"bar_buy": "", "bar_sell": "", "ornament_buy": "", "ornament_sell": ""}

    # 1) โครงแบบตารางที่มี class="table-price"
    table = soup.find("table", class_="table-price")
    if table:
        for row in table.find_all("tr"):
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 3:
                name = cols[0]
                buy  = _clean_num(cols[1])
                sell = _clean_num(cols[2])
                if "ทองคำแท่ง" in name:
                    prices["bar_buy"] = buy or prices["bar_buy"]
                    prices["bar_sell"] = sell or prices["bar_sell"]
                elif "ทองรูปพรรณ" in name:
                    prices["ornament_buy"] = buy or prices["ornament_buy"]
                    prices["ornament_sell"] = sell or prices["ornament_sell"]

    # 2) เผื่อบางธีมปรับ class ชื่ออื่น — หาแถวที่มีคำบนทั้งหน้า
    text_tables = soup.find_all("table")
    if not any(prices.values()):
        for t in text_tables:
            txt = t.get_text(" ", strip=True)
            if ("ทองคำแท่ง" in txt or "ทองรูปพรรณ" in txt) and ("รับซื้อ" in txt or "ขายออก" in txt):
                # ลองหาทีละบรรทัดที่กล่าวถึง
                for row in t.find_all("tr"):
                    line = row.get_text(" ", strip=True)
                    if "ทองคำแท่ง" in line:
                        m = re.findall(r"(\d[\d,\.]*)", line.translate(_TH2AR))
                        if len(m) >= 2:
                            prices["bar_buy"]  = _clean_num(m[0])
                            prices["bar_sell"] = _clean_num(m[1])
                    if "ทองรูปพรรณ" in line:
                        m = re.findall(r"(\d[\d,\.]*)", line.translate(_TH2AR))
                        if len(m) >= 2:
                            prices["ornament_buy"]  = _clean_num(m[0])
                            prices["ornament_sell"] = _clean_num(m[1])

    # 3) ถ้ายังไม่เจอ ลองดู span/div ที่มีข้อมูลตัวเลขคู่ ๆ
    if not any(prices.values()):
        blocks = soup.find_all(["div", "span", "li", "p"])
        for b in blocks:
            line = b.get_text(" ", strip=True)
            if "ทองคำแท่ง" in line and ("รับซื้อ" in line or "ขายออก" in line):
                m = re.findall(r"(\d[\d,\.]*)", line.translate(_TH2AR))
                if len(m) >= 2:
                    prices["bar_buy"]  = _clean_num(m[0])
                    prices["bar_sell"] = _clean_num(m[1])
            if "ทองรูปพรรณ" in line and ("รับซื้อ" in line or "ขายออก" in line):
                m = re.findall(r"(\d[\d,\.]*)", line.translate(_TH2AR))
                if len(m) >= 2:
                    prices["ornament_buy"]  = _clean_num(m[0])
                    prices["ornament_sell"] = _clean_num(m[1])

    return updated, prices

def _format_msg_from_gta(updated: Optional[str], p: Dict[str, str]) -> Optional[str]:
    lines = []
    if any(p.values()):
        lines.append("📅 ราคาทองวันนี้ (สมาคมค้าทองคำ)")
        if updated:
            lines.append(f"• {updated}")
        if p.get("bar_buy") or p.get("bar_sell"):
            lines.append(f"ทองคำแท่ง: รับซื้อ {p.get('bar_buy','-')} / ขายออก {p.get('bar_sell','-')} บาท")
        if p.get("ornament_buy") or p.get("ornament_sell"):
            lines.append(f"ทองรูปพรรณ: รับซื้อ {p.get('ornament_buy','-')} / ขายออก {p.get('ornament_sell','-')} บาท")
        lines.append("")
        lines.append("ดูกราฟและข้อมูลละเอียด: https://www.goldtraders.or.th/")
        return "\n".join(lines)
    return None

# ------------------- Public API -------------------
def get_gold_price() -> str:
    """
    คืนราคาทองคำวันนี้ (สมาคมค้าทองคำ ถ้า scrape ไม่ได้จะ fallback GoldAPI.io)
    """
    # ---------- 1) Scrape ราคาจากสมาคมค้าทอง ----------
    try:
        session = _build_session(timeout=10, retries=2, backoff=0.6)
        url = "https://www.goldtraders.or.th/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        }
        resp = session.get(url, headers=headers)
        if resp.status_code == 200 and resp.text:
            updated, prices = _parse_goldtraders(resp.text)
            msg = _format_msg_from_gta(updated, prices)
            if msg:
                return msg
        else:
            print(f"[gold_utils] goldtraders http {resp.status_code}")
    except Exception as e:
        print(f"[gold_utils] error goldtraders: {e}")

    # ---------- 2) Fallback ไป GoldAPI.io (spot) ----------
    GOLD_API_KEY = os.getenv("GOLDAPI_KEY")
    if GOLD_API_KEY:
        url = "https://www.goldapi.io/api/XAU/THB"
        headers = {"x-access-token": GOLD_API_KEY, "Content-Type": "application/json"}
        try:
            session = _build_session(timeout=10, retries=2, backoff=0.6)
            resp = session.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                price = data.get("price")
                if price:
                    # 1 ออนซ์ ≈ 31.1035 กรัม, 1 บาททอง (ไทย) ≈ 15.244 กรัม
                    price_per_gram = float(price) / 31.1035
                    price_per_baht = price_per_gram * 15.244
                    # ปัดลงเป็นหลักสิบ (ตามตลาดชอบเคาะเป็นขั้น)
                    price_per_baht = int(price_per_baht // 10 * 10)
                    return (
                        "📅 ราคาทองคำอัปเดต (Spot XAU/THB จาก GoldAPI.io)\n"
                        f"ทองคำแท่งขายออก ~ {price_per_baht:,} บาท/บาททอง\n"
                        "(คำนวณจาก spot ไม่รวมค่ากำเหน็จ/พรีเมียมตลาดไทย)\n"
                        "ดูราคาตลาดไทย: https://www.goldtraders.or.th/"
                    )
            else:
                print(f"[gold_utils] GoldAPI http {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"[gold_utils] GoldAPI error: {e}")

    # ---------- 3) Fallback mock ถ้าไม่มี api key หรือ error ----------
    return (
        "📅 ราคาทองคำวันนี้ (ข้อมูลตัวอย่าง)\n"
        "ทองคำแท่ง: รับซื้อ 38,000 / ขายออก 38,100 บาท\n"
        "ทองรูปพรรณ: รับซื้อ 37,500 / ขายออก 38,600 บาท"
    )
