from __future__ import annotations

import hashlib
import re

# Thứ tự quan trọng: pattern tổng quát phải đứng sau pattern cụ thể hơn, ví dụ
# email trước CCCD, để không bị che sai phần dữ liệu.

# "12 Nguyễn Trãi" hoặc "45 Lê Lợi" — số nhà + tên đường viết hoa chữ đầu.
_VN_STREET = r"\d{1,4}\s+(?:[A-ZĐ][\wÀ-ỹ]*\s+){0,3}[A-ZĐ][\wÀ-ỹ]*"
# "Phường Bến Nghệ", "Quận 1", "Thị xã Thủ Dầu Một" — dấu hiệu hành chính.
_VN_ADMIN = (
    r"(?:Phường|Ph\.|Quận|Qu\.|Huyện|Huy\.|Thị\s*xã|Thành\s*phố|Tỉnh)"
    r"\s*[A-ZĐ]?[\wÀ-ỹ.]*(?:\s+[A-ZĐ][\wÀ-ỹ.]*)*"
)

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "cccd": r"\b\d{12}\b",
    "passport": r"\b[A-Z]{1,2}\d{7}\b",
    "vn_address": rf"{_VN_STREET},\s*{_VN_ADMIN}(?:[\s,]+{_VN_ADMIN})*",
}

PII_LABELS: tuple[str, ...] = tuple(PII_PATTERNS)


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
