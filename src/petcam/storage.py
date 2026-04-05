"""Recording file retention.

`list_clips` enumerates MP4 files in a directory with metadata; `cleanup` deletes
files that exceed the retention window or push total size past the limit.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ClipInfo:
    filename: str
    path: Path
    size_bytes: int
    created_at: datetime


def list_clips(directory: Path) -> list[ClipInfo]:
    """Return MP4 clips in `directory`, newest first."""
    if not directory.exists():
        return []
    clips: list[ClipInfo] = []
    for entry in directory.iterdir():
        if not entry.is_file() or entry.suffix.lower() != ".mp4":
            continue
        stat = entry.stat()
        clips.append(
            ClipInfo(
                filename=entry.name,
                path=entry,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )
    clips.sort(key=lambda c: c.created_at, reverse=True)
    return clips


def cleanup(directory: Path, retain_days: int, max_total_gb: float) -> list[str]:
    """Delete stale and oversized clips. Returns removed filenames."""
    removed: list[str] = []
    if not directory.exists():
        return removed

    now = time.time()
    cutoff = now - retain_days * 86400
    remaining: list[tuple[float, Path, int]] = []  # (mtime, path, size)

    # 1) Drop files older than retain_days.
    for entry in directory.iterdir():
        if not entry.is_file() or entry.suffix.lower() != ".mp4":
            continue
        stat = entry.stat()
        if stat.st_mtime < cutoff:
            entry.unlink()
            removed.append(entry.name)
        else:
            remaining.append((stat.st_mtime, entry, stat.st_size))

    # 2) Enforce total size cap by deleting oldest first.
    max_bytes = int(max_total_gb * (1024**3))
    total = sum(size for _, _, size in remaining)
    if total > max_bytes:
        remaining.sort(key=lambda t: t[0])  # oldest first
        for _, path, size in remaining:
            if total <= max_bytes:
                break
            path.unlink()
            removed.append(path.name)
            total -= size

    return removed
