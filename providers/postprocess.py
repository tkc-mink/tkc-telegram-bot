# utils/postprocess.py
# -*- coding: utf-8 -*-
import re

_NO_ECHO_PREFIXES = re.compile(
    r"^\s*(รับทราบ(?:ครับ|ค่ะ|นะ)?|คุณ\s*ถามว่า|สรุปคำถาม|ยืนยันคำถาม|คำถามของคุณ|Question|You\s+asked)[:：-]\s*",
    re.IGNORECASE | re.UNICODE,
)

def strip_no_echo_prefix(text: str) -> str:
    return _NO_ECHO_PREFIXES.sub("", text or "", count=1)

def safe_truncate(text: str, n: int = 4000) -> str:
    t = text or ""
    return t if len(t) <= n else t[:n]
