# handlers/__init__.py

# Export ฟังก์ชันหลักให้ main.py ใช้งาน
from .main_handler import handle_message

# หมายเหตุ:
# คุณไม่จำเป็นต้อง import handler ย่อยอื่นๆ ที่ไม่ได้ใช้ตรงนี้
# เว้นแต่ว่าคุณต้องการให้ฟังก์ชัน/คลาสอื่นๆ export ออกไปทั้ง package (ไม่จำเป็นสำหรับ main.py ปกติ)
