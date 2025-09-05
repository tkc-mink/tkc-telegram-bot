import os
import tempfile
import shutil
import time

def create_temp_file(suffix: str = "") -> str:
    """สร้างไฟล์ชั่วคราวและคืน path (พยายามตั้ง perm 0o600 บน POSIX)"""
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()
        if os.name == "posix":
            try:
                os.chmod(tmp.name, 0o600)
            except Exception:
                pass
        return tmp.name
    except Exception as e:
        print(f"[file_utils] Tempfile error: {e}")
        return ""

def remove_file(path: str) -> bool:
    """ลบไฟล์ หากมีอยู่ (retry เล็กน้อยเพื่อกัน Windows lock)"""
    if not path:
        return False
    last_err = None
    for _ in range(3):
        try:
            if not os.path.exists(path):
                return True
            os.remove(path)
            return True
        except PermissionError:
            # เผื่อเป็น read-only บน Windows/NTFS
            try:
                os.chmod(path, 0o666)
            except Exception:
                pass
            last_err = "PermissionError"
        except Exception as e:
            last_err = e
        time.sleep(0.1)
    print(f"[file_utils] Remove error: {last_err}")
    return False

def get_file_size(path: str) -> int:
    """คืนขนาดไฟล์ (byte) หรือ -1 หากไม่พบ/เข้าถึงไม่ได้"""
    try:
        return os.path.getsize(path)
    except Exception:
        return -1

def copy_file(src: str, dst: str) -> bool:
    """
    copy ไฟล์แบบ atomic:
    - ถ้า dst เป็นโฟลเดอร์ จะคัดลอกเป็น <dst>/<basename(src)>
    - คัดลอกไป temp ในโฟลเดอร์ปลายทาง แล้วใช้ os.replace ทับ (ลดโอกาสไฟล์ครึ่ง ๆ กลาง ๆ)
    """
    try:
        if not os.path.isfile(src):
            print(f"[file_utils] Copy error: source not a file: {src}")
            return False

        # คำนวณ path ปลายทางจริง
        target = os.path.join(dst, os.path.basename(src)) if os.path.isdir(dst) else dst
        target_dir = os.path.dirname(target) or "."
        os.makedirs(target_dir, exist_ok=True)

        # ถ้า src == target ให้ถือว่าสำเร็จ
        if os.path.abspath(src) == os.path.abspath(target):
            return True

        # สร้าง temp ในโฟลเดอร์เดียวกับปลายทาง เพื่อให้ os.replace เป็น atomic บน FS เดียวกัน
        fd, tmp_path = tempfile.mkstemp(prefix=".copy-", dir=target_dir)
        os.close(fd)
        try:
            shutil.copy2(src, tmp_path)  # เก็บ metadata เท่าที่ทำได้
            os.replace(tmp_path, target)
            return True
        finally:
            # เผื่อกรณีมี exception ค้าง temp ไว้
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
    except Exception as e:
        print(f"[file_utils] Copy error: {e}")
        return False
