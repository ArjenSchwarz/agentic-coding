"""Secret redaction for failure messages.

The page is archived and served to feed readers, and test output routinely
carries tokens and connection strings. ``PATTERNS`` are applied in order and
every match becomes ``[redacted]``; ``clean_message`` redacts before it
truncates so a secret straddling the cut can never survive.
"""
from __future__ import annotations

import re

PATTERNS: list[re.Pattern] = [
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]+"),
    re.compile(r"""(?i)[A-Za-z0-9_]*(key|token|secret|password|passwd|pwd)["']?\s*[=:]\s*\S+"""),
    re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]

REDACTED = "[redacted]"
MESSAGE_LIMIT = 500


def redact(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


def clean_message(text: str, limit: int = MESSAGE_LIMIT) -> str:
    """Redact, then cap at ``limit`` characters with a trailing ellipsis."""
    text = redact(text)
    if len(text) > limit:
        return text[:limit - 1] + "…"
    return text
