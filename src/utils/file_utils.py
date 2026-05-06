"""File-system helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not already exist."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text to disk, ensuring the parent directory exists."""

    ensure_directory(path.parent)
    path.write_text(content, encoding="utf-8")
    return path


def read_text(path: Path) -> str:
    """Read UTF-8 text from disk."""

    return path.read_text(encoding="utf-8")
