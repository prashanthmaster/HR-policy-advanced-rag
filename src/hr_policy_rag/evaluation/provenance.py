"""Cross-platform identity helpers for immutable evaluation evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_text_sha256(path: Path) -> str:
    """Hash UTF-8 logical text with LF newlines on every operating system."""

    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode()).hexdigest()
