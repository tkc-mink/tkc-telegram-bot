# utils/history_utils.py
# -*- coding: utf-8 -*-
"""
User Q/A History (hardened)
- Atomic write + .bak backup + cross-process file lock
- Safe read (handles empty/corrupt/BOM; fallback to .bak)
- Thread-safe in-process via RLock
- get_user_history returns latest-first
"""

import os
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from threading import RLock
import io
import time

# ---- CONFIG ----
HISTORY_FILE = os.getenv("HISTORY_FILE", "data/history.json")
MAX_RECORDS_PER_USER = max(1, int(os.getenv("MAX_HISTORY_PER_USER", "100")))
MAX_HISTORY_BYTES = int(os.getenv("MAX_HISTORY_BYTES", str(20 * 1024 * 1024)))  # 20MB cap
BACKUP_EXT = os.getenv("HISTORY_BACKUP_EXT", ".bak")
LOCK_TIMEOUT = float(os.getenv("HISTORY_LOCK_TIMEOUT", "5.0"))
LOCK_POLL = float(os.getenv("HISTORY_LOCK_POLL", "0.05"))

# ใช้ตัวแปร global lock แบบง่ายๆ กันเขียนพร้อมกันหลายครั้งใน process เดียว
_LOCK = RLock()

# ---------- minimal cross-process lock ----------
IS_WIN = os.name == "nt"
try:
    if IS_WIN:
        import msvcrt
    else:
        import fcntl
except Exception:
    msvcrt = None
    fcntl = None


class _FileLock:
    """
    ใช้ไฟล์ .lock คู่กับ HISTORY_FILE (cross-process)
    - exclusive=True: เขียน
    - exclusive=False: อ่าน
    """
    def __init__(self, lock_path: str, timeout: float = LOCK_TIMEOUT, poll: float = LOCK_POLL):
        self.lock_path = lock_path
        self.timeout = timeout
        self.poll = poll
        self._fh: Optional[io.TextIOBase] = None

    def acquire(self, exclusive: bool = True):
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
        start = time.time()
        self._fh = open(self.lock_path, "a+")
        while True:
            try:
                if IS_WIN and msvcrt:
                    mode = msvcrt.LK_NBLCK if exclusive else getattr(msvcrt, "LK_NBRLCK", msvcrt.LK_NBLCK)
                    try:
                        msvcrt.locking(self._fh.fileno(), mode, 1)
                        break
                    except OSError:
                        pass
                elif fcntl:
                    flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                    fcntl.flock(self._fh.fileno(), flags | fcntl.LOCK_NB)
                    break
                else:
                    # ถ้าล็อกไม่ได้จริง ๆ ก็ปล่อยผ่าน (ยังมี atomic write ช่วยอยู่)
                    break
            except OSError:
                if time.time() - start >= self.timeout:
                    raise TimeoutError(f"Lock timeout: {self.lock_path}")
                time.sleep(self.poll)
        return self

    def release(self):
        try:
            if self._fh:
                if IS_WIN and msvcrt:
                    try:
                        msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                elif fcntl:
                    try:
                        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
                self._fh.close()
                self._fh = None
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()


# ---------- Low level helpers ----------
def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

def _strip_bom(txt: str) -> str:
    return txt.lstrip("\ufeff")

def _atomic_write_bytes(data: bytes, path: str) -> None:
    """เขียนไฟล์แบบ atomic: เขียนลง temp แล้ว os.replace ทับไฟล์จริง (พร้อม fsync)"""
    _ensure_parent_dir(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".hist-", suffix=".tmp", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _read_json_file(path: str, default: Any) -> Any:
    """อ่าน JSON แบบทนทาน + cap ขนาด + โยน default หากมีปัญหา"""
    try:
        if not os.path.exists(path):
            return default
        if MAX_HISTORY_BYTES and os.path.getsize(path) > MAX_HISTORY_BYTES:
            print(f"[history_utils] {path} too large (> {MAX_HISTORY_BYTES} bytes); returning default")
            return default
        with open(path, "rb") as f:
            raw = f.read()
        if not raw:
            return default
        txt = _strip_bom(raw.decode("utf-8", errors="replace"))
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            txt2 = txt.strip()
            if not txt2:
                return default
            try:
                return json.loads(txt2)
            except Exception as e:
                print(f"[history_utils] JSON decode failed: {e}; returning default")
                return default
    except Exception as e:
        print(f"[history_utils] read failed: {e}; returning default")
        return default

def _write_json_file(data: Any, path: str) -> None:
    """สำรอง .bak (ถ้ามี), เขียนแบบ atomic"""
    try:
        # backup เดิม (ถ้ามี)
        if BACKUP_EXT and os.path.exists(path):
            try:
                with open(path, "rb") as rf:
                    old = rf.read()
                _atomic_write_bytes(old, f"{path}{BACKUP_EXT}")
            except Exception as be:
                print(f"[history_utils] backup failed: {be}")
        # เขียนจริง
        _atomic_write_bytes(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"), path)
    except Exception as e:
        print(f"[history_utils] write failed: {e}")
        raise

def _rw_update_atomic(path: str, updater) -> Any:
    """
    อ่าน->อัปเดต->เขียน ภายใต้ 'exclusive file lock' เดียว (cross-process safe)
    - updater: fn(data_dict) -> data_dict (mutate/return)
    """
    lock_path = f"{path}.lock"
    with _FileLock(lock_path, timeout=LOCK_TIMEOUT).acquire(exclusive=True):
        data = _read_json_file(path, default={})
        new_data = updater(data if isinstance(data, dict) else {})
        _write_json_file(new_data, path)
        return new_data


# ---------- Public APIs ----------
def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """โหลดประวัติทั้งหมด (dict[user_id] = list[record])"""
    with _LOCK:
        lock_path = f"{HISTORY_FILE}.lock"
        try:
            with _FileLock(lock_path, timeout=LOCK_TIMEOUT).acquire(exclusive=False):
                data = _read_json_file(HISTORY_FILE, default={})
                return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[history_utils.load_history] {e}")
            return {}

def save_history(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """บันทึกประวัติทั้งหมด"""
    with _LOCK:
        try:
            _rw_update_atomic(HISTORY_FILE, lambda _old: data if isinstance(data, dict) else {})
        except Exception as e:
            print(f"[history_utils.save_history] {e}")

def log_message(user_id: str, question: str, answer: str) -> None:
    """
    บันทึก Q/A ของผู้ใช้ 1 รายการ
    - เก็บได้สูงสุด MAX_RECORDS_PER_USER รายการล่าสุด
    - เขียนแบบ atomic ภายใต้ cross-process lock
    """
    uid = str(user_id)
    ts = datetime.now().isoformat(timespec="seconds")
    with _LOCK:
        try:
            def _update(old: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
                records = old.setdefault(uid, [])
                records.append({"date": ts, "q": question, "a": answer})
                old[uid] = records[-MAX_RECORDS_PER_USER:]
                return old
            _rw_update_atomic(HISTORY_FILE, _update)
        except Exception as e:
            print(f"[history_utils.log_message] {e}")

def get_user_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """ดึงประวัติของผู้ใช้ (ล่าสุดก่อน)"""
    data = load_history()
    history = data.get(str(user_id), [])
    # คืนล่าสุดก่อนตามสเปค
    return list(reversed(history))[:max(1, int(limit))]

# ------- Optional helper functions -------
def clear_user_history(user_id: str) -> None:
    """ลบประวัติของ user คนเดียว"""
    with _LOCK:
        try:
            def _update(old: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
                old.pop(str(user_id), None)
                return old
            _rw_update_atomic(HISTORY_FILE, _update)
        except Exception as e:
            print(f"[history_utils.clear_user_history] {e}")

def export_all_history() -> Dict[str, List[Dict[str, Any]]]:
    """คืนค่าประวัติทั้งหมด (สำหรับ backup/export)"""
    return load_history()
