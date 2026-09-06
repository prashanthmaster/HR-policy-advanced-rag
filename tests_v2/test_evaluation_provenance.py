from __future__ import annotations

from pathlib import Path

from hr_policy_rag.evaluation import canonical_text_sha256


def test_text_identity_is_stable_across_windows_and_linux_newlines(tmp_path: Path) -> None:
    linux = tmp_path / "linux.lock"
    windows = tmp_path / "windows.lock"
    linux.write_bytes(b"version = 1\nrevision = 3\n")
    windows.write_bytes(b"version = 1\r\nrevision = 3\r\n")

    assert canonical_text_sha256(linux) == canonical_text_sha256(windows)
