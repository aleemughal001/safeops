"""Telemetry sanitizer MVP.

This module masks common sensitive values before evidence is sent to an AI model.
"""

import re
from typing import Dict, Any

PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*[^\s]+"), r"\1=***REDACTED***"),
    (re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*[^\s]+"), r"\1=***REDACTED***"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "***EMAIL_REDACTED***"),
]


def sanitize_text(text: str) -> str:
    clean = text
    for pattern, replacement in PATTERNS:
        clean = pattern.sub(replacement, clean)
    return clean


def sanitize_evidence_item(item: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(item)
    if "summary" in item and isinstance(item["summary"], str):
        item["summary"] = sanitize_text(item["summary"])
    return item
