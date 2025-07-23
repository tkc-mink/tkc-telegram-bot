import os
import tempfile
import shutil

def create_temp_file(suffix=""):
    """สร้างไฟล์ชั่วคราวและคืน path"""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    return tmp.name

def remove_file(path):
    """ลบไฟล์ หากมีอยู่"""
    try:
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception as e:
        print(f"[file_utils] Remove error: {e}")
    return False

def get_file_size(path):
    """คืนขนาดไฟล์ (byte) หรือ -1 หากไม่พบ"""
    try:
        return os.path.getsize(path)
    except Exception:
        return -1

def copy_file(src, dst):
    """copy ไฟล์ (return True/False)"""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"[file_utils] Copy error: {e}")
        return False
