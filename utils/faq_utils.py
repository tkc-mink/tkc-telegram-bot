# utils/faq_utils.py
# -*- coding: utf-8 -*-
"""
FAQ utilities (hardened, drop-in compatible)
- ใช้ persistent DB ผ่าน utils.memory_store ถ้ามี
- ถ้า DB ใช้ไม่ได้: fallback เป็นไฟล์ JSON (atomic write + สำรอง)
- คง API เดิม:
    get_faq_list() -> List[str]  (ค่าเริ่มต้นคืนเฉพาะ keyword)
    add_faq(q) -> None/Bool      (รับได้ทั้ง str หรือ dict{'keyword','answer'})
- เพิ่มออปชัน:
    get_faq_list(include_answers=True) -> List[Dict[str,str]]
    add_faq(q, answer=None, added_by=None) -> bool
    get_faq_answer(keyword) -> Optional[str]
    get_all_faqs() -> List[Dict[str,str]]
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
import os
import json
import tempfile

# -------- settings --------
FAQ_FILE = os.getenv("FAQ_FILE", "data/faq_list.json")
_BACKUP_EXT = ".bak"

# -------- try DB backend --------
_USE_DB = False
try:
    from utils.memory_store import (
        add_or_update_faq as _db_add_or_update_faq,
        get_faq_answer as _db_get_faq_answer,
        get_all_faqs as _db_get_all_faqs,
    )
    _USE_DB = True
except Exception as e:
    print(f"[faq_utils] DB backend not available, using JSON file. ({e})")


# -------- file helpers (atomic, resilient) --------
def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

def _atomic_write_json(data: Any, path: str) -> None:
    _ensure_dir(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".faq-", suffix=".tmp", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        # backup เก่า
        if os.path.exists(path):
            try:
                with open(path, "rb") as rf:
                    old = rf.read()
                bak = f"{path}{_BACKUP_EXT}"
                fd2, tmp_bak = tempfile.mkstemp(prefix=".faq-bak-", suffix=".tmp", dir=os.path.dirname(bak) or ".")
                with os.fdopen(fd2, "wb") as bf:
                    bf.write(old)
                    bf.flush()
                    try:
                        os.fsync(bf.fileno())
                    except Exception:
                        pass
                os.replace(tmp_bak, bak)
            except Exception as e:
                print(f"[faq_utils] backup failed: {e}")
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _load_json_resilient(path: str, default: Any) -> Any:
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[faq_utils] read JSON failed: {e}")
        # fallback .bak
        bak = f"{path}{_BACKUP_EXT}"
        try:
            if os.path.exists(bak):
                with open(bak, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e2:
            print(f"[faq_utils] read backup failed: {e2}")
        return default


# -------- public APIs (drop-in) --------
def get_faq_list(include_answers: bool = False) -> List[Any]:
    """
    ค่าเริ่มต้น: คืนเฉพาะรายการ keyword (list[str]) เพื่อคงพฤติกรรมเดิม
    include_answers=True: คืน list[{'keyword','answer'}]
    """
    if _USE_DB:
        faqs = _db_get_all_faqs() or []  # [{'keyword','answer'}]
        if include_answers:
            return faqs
        return [it.get("keyword", "") for it in faqs if it.get("keyword")]
    else:
        data = _load_json_resilient(FAQ_FILE, default=[])
        # รองรับทั้งรูปแบบเดิม (list[str]) และแบบ dict
        if include_answers:
            if isinstance(data, list):
                out: List[Dict[str, str]] = []
                for it in data:
                    if isinstance(it, dict):
                        kw = str(it.get("keyword", "")).strip()
                        ans = str(it.get("answer", "")).strip()
                        if kw:
                            out.append({"keyword": kw, "answer": ans})
                    else:
                        kw = str(it).strip()
                        if kw:
                            out.append({"keyword": kw, "answer": ""})
                return out
            return []
        else:
            if isinstance(data, list):
                kws: List[str] = []
                for it in data:
                    if isinstance(it, dict):
                        kw = str(it.get("keyword", "")).strip()
                        if kw:
                            kws.append(kw)
                    else:
                        kw = str(it).strip()
                        if kw:
                            kws.append(kw)
                return kws
            return []


def add_faq(q: Any, answer: Optional[str] = None, added_by: Optional[int] = None) -> bool:
    """
    เพิ่ม FAQ (drop-in):
    - ถ้า q เป็น str: ใช้เป็น keyword
    - ถ้า q เป็น dict: รองรับ {'keyword':..., 'answer':...}
    - ถ้ามี DB: บันทึกลงตาราง faq (UPSERT) โดยจะแปลง keyword เป็น lower-side ใน layer DB อยู่แล้ว
    - ถ้าเป็นไฟล์: เก็บเป็น list (รองรับทั้ง str และ dict) และ dedup ตาม keyword
    """
    # normalize input
    if isinstance(q, dict):
        keyword = str(q.get("keyword", "")).strip()
        ans = q.get("answer", None)
        if ans is not None:
            answer = str(ans)
    else:
        keyword = str(q or "").strip()

    if not keyword:
        print("[faq_utils] Empty keyword")
        return False
    if answer is None:
        answer = ""

    if _USE_DB:
        try:
            user_id = int(added_by) if added_by is not None else 0
            ok = _db_add_or_update_faq(keyword, answer, user_id)
            return bool(ok)
        except Exception as e:
            print(f"[faq_utils] DB add/update failed: {e}")
            # fall through to file
    # file backend
    try:
        data = _load_json_resilient(FAQ_FILE, default=[])
        # normalize to list
        if not isinstance(data, list):
            data = []

        # dedup by keyword (case-insensitive)
        norm = keyword.lower()
        found = False
        new_data: List[Any] = []
        for it in data:
            if isinstance(it, dict):
                kw = str(it.get("keyword", "")).strip()
                if kw.lower() == norm:
                    # update/overwrite answer
                    it["keyword"] = keyword
                    if answer is not None:
                        it["answer"] = str(answer)
                    found = True
            elif isinstance(it, str):
                if it.strip().lower() == norm:
                    # upgrade to dict if answer provided
                    it = {"keyword": keyword, "answer": str(answer or "")}
                    found = True
            new_data.append(it)

        if not found:
            # append; ถ้าไม่มีคำตอบ ให้เก็บเป็น str เพื่อเข้ากับโค้ดเก่า
            if (answer or "").strip():
                new_data.append({"keyword": keyword, "answer": str(answer)})
            else:
                new_data.append(keyword)

        _atomic_write_json(new_data, FAQ_FILE)
        return True
    except Exception as e:
        print(f"[faq_utils] file add/update failed: {e}")
        return False


# -------- convenience wrappers --------
def get_faq_answer(keyword: str) -> Optional[str]:
    """
    คืนคำตอบของ keyword ถ้ามี
    """
    kw = (keyword or "").strip()
    if not kw:
        return None

    if _USE_DB:
        try:
            return _db_get_faq_answer(kw)
        except Exception as e:
            print(f"[faq_utils] DB get_faq_answer error: {e}")

    # file backend
    data = _load_json_resilient(FAQ_FILE, default=[])
    if isinstance(data, list):
        norm = kw.lower()
        for it in data:
            if isinstance(it, dict):
                k = str(it.get("keyword", "")).strip()
                if k and k.lower() == norm:
                    return str(it.get("answer", "")).strip() or None
    return None


def get_all_faqs() -> List[Dict[str, str]]:
    """
    คืนรายการทั้งหมดเป็นโครงสร้าง [{keyword, answer}]
    """
    return get_faq_list(include_answers=True)  # reuse
