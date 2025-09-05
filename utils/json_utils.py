# utils/json_utils.py
# -*- coding: utf-8 -*-
"""
Hardened JSON I/O helpers (drop-in safe versions)
- load_json_safe: ปลอดภัยต่อไฟล์หาย/ไฟล์ว่าง/อ่านไม่ได้/โดนเขียนค้าง (+ fallback .bak)
- save_json_safe: เขียนแบบ atomic + สำรอง .bak + สร้างโฟลเดอร์อัตโนมัติ
- Cross-platform file lock (Windows/Linux) กันชนกันข้ามโปรเซส
- มีตัวเลือกปรับแต่งผ่านพารามิเตอร์
"""

from __future__ import annotations
from typing import Any, Optional, Union
import json
import os
import io
import time
import tempfile

# ---------- minimal cross-platform lock ----------
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
    ใช้ไฟล์ .lock แยกจากตัวไฟล์จริง (ปลอดภัยเมื่อเขียนแบบ atomic ด้วย os.replace)
    - exclusive=True: เขียน
    - exclusive=False: อ่าน
    """
    def __init__(self, lock_path: str, timeout: float = 5.0, poll: float = 0.05):
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
                    # Windows: msvcrt ใช้ byte-range lock; ใช้โหมด non-blocking ทั้งอ่าน/เขียน
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


# ---------- helpers ----------
def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)

def _atomic_write_bytes(data: bytes, path: str) -> None:
    """เขียนไฟล์แบบ atomic: เขียนลง temp แล้ว os.replace ทับไฟล์จริง"""
    _ensure_dir(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path) or ".")
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

def _strip_bom(txt: str) -> str:
    return txt.lstrip("\ufeff")

def _fs(path: Union[str, os.PathLike]) -> str:
    return os.fspath(path)


# ---------- public APIs (drop-in) ----------
def load_json_safe(
    path: Union[str, os.PathLike],
    default: Any = None,
    *,
    lock_timeout: float = 5.0,
    max_bytes: Optional[int] = 10 * 1024 * 1024,  # กันไฟล์ใหญ่เกิน (10MB)
    use_backup: bool = True,
    backup_ext: str = ".bak",
) -> Any:
    """
    อ่าน JSON อย่างปลอดภัย:
    - ถ้าไฟล์ไม่มี/ว่าง/เสีย -> คืน default (หรือ {})
    - ล็อกอ่านข้ามโปรเซสผ่านไฟล์ .lock
    - กันไฟล์ใหญ่เกินด้วย max_bytes
    - ถ้าไฟล์หลักเสีย และ use_backup=True -> พยายามอ่านไฟล์สำรอง *.bak
    """
    path = _fs(path)
    if default is None:
        default = {}

    def _try_load(p: str) -> Any:
        # read lock
        lock_path = f"{p}.lock"
        with _FileLock(lock_path, timeout=lock_timeout).acquire(exclusive=False):
            # quick size check
            if max_bytes is not None:
                try:
                    if os.path.getsize(p) > max_bytes:
                        print(f"[load_json_safe:{p}] file too large; returning default")
                        return default
                except OSError:
                    return default

            try:
                with open(p, "rb") as f:
                    raw = f.read()
            except OSError:
                return default

        if not raw:
            return default

        # decode -> handle BOM
        txt = _strip_bom(raw.decode("utf-8", errors="replace"))
        try:
            return json.loads(txt)
        except json.JSONDecodeError as e:
            # ลองตัดช่องว่าง/บรรทัดว่างท้ายไฟล์ (บางทีเขียนไม่จบ)
            txt2 = txt.strip()
            if not txt2:
                return default
            try:
                return json.loads(txt2)
            except Exception as e2:
                print(f"[load_json_safe:{p}] JSONDecodeError -> {e2}; returning default")
                return default

    # main
    if not os.path.exists(path):
        return default

    obj = _try_load(path)
    if obj != default:
        return obj

    # fallback: read backup
    if use_backup and backup_ext:
        bak = f"{path}{backup_ext}"
        if os.path.exists(bak):
            obj_bak = _try_load(bak)
            if obj_bak != default:
                print(f"[load_json_safe:{path}] loaded from backup {bak}")
                return obj_bak

    return default


def save_json_safe(
    data: Any,
    path: Union[str, os.PathLike],
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    backup_ext: Optional[str] = ".bak",
    lock_timeout: float = 5.0,
) -> bool:
    """
    เขียน JSON อย่างปลอดภัย:
    - เขียน temp -> fsync -> os.replace (atomic)
    - ทำสำรองไฟล์เดิมเป็น .bak (ถ้ามีและ backup_ext ไม่เป็น None)
    - ล็อกเขียนข้ามโปรเซสผ่านไฟล์ .lock
    """
    path = _fs(path)
    try:
        # exclusive lock
        lock_path = f"{path}.lock"
        with _FileLock(lock_path, timeout=lock_timeout).acquire(exclusive=True):
            # สำรองไฟล์เดิม
            if backup_ext and os.path.exists(path):
                try:
                    bak_path = f"{path}{backup_ext}"
                    with open(path, "rb") as rf:
                        old = rf.read()
                    _atomic_write_bytes(old, bak_path)
                except Exception as be:
                    print(f"[save_json_safe:{path}] backup failed: {be}")

            # serialize -> bytes
            try:
                txt = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys)
            except (TypeError, ValueError) as se:
                # เผื่อมี object แปลก ๆ ที่ serialize ไม่ได้
                print(f"[save_json_safe:{path}] serialize error: {se}; trying default(str(obj))")
                def _fallback(o):
                    return str(o)
                txt = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys, default=_fallback)

            _atomic_write_bytes(txt.encode("utf-8"), path)
        return True
    except Exception as e:
        print(f"[save_json_safe:{path}] {e}")
        return False


# ---------- optional utilities ----------
def append_jsonl_safe(obj: Any, path: Union[str, os.PathLike], *, lock_timeout: float = 5.0) -> bool:
    """
    บันทึก 1 record ต่อบรรทัด (JSON Lines) แบบปลอดภัย + ล็อกไฟล์
    หมายเหตุ: วิธีนี้อ่านไฟล์ทั้งก้อนเพื่อรวม (atomic replace) จึงไม่เหมาะกับไฟล์ใหญ่มาก
    """
    path = _fs(path)
    try:
        lock_path = f"{path}.lock"
        with _FileLock(lock_path, timeout=lock_timeout).acquire(exclusive=True):
            _ensure_dir(path)
            line = json.dumps(obj, ensure_ascii=False)

            # ถ้ามีไฟล์หลัก -> concat ในหน่วยความจำแล้ว replace
            if os.path.exists(path):
                with open(path, "rb") as rf:
                    prev = rf.read()
                data = prev + line.encode("utf-8") + b"\n"
                _atomic_write_bytes(data, path)
            else:
                # เขียนบรรทัดเดียวแบบ atomic
                _atomic_write_bytes((line + "\n").encode("utf-8"), path)
        return True
    except Exception as e:
        print(f"[append_jsonl_safe:{path}] {e}")
        return False
