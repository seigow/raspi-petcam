import os
import time
from pathlib import Path

from petcam.storage import ClipInfo, cleanup, list_clips


def make_clip(dir_path: Path, name: str, size_bytes: int, age_seconds: float) -> Path:
    """Create a fake MP4 file with the given size and mtime."""
    path = dir_path / name
    path.write_bytes(b"\x00" * size_bytes)
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


def test_list_clips_returns_info_sorted_newest_first(tmp_path: Path) -> None:
    make_clip(tmp_path, "old.mp4", 100, age_seconds=3600)
    make_clip(tmp_path, "new.mp4", 200, age_seconds=10)
    make_clip(tmp_path, "middle.mp4", 150, age_seconds=600)
    # Non-mp4 files should be ignored.
    (tmp_path / "note.txt").write_text("ignore me")

    clips = list_clips(tmp_path)

    assert [c.filename for c in clips] == ["new.mp4", "middle.mp4", "old.mp4"]
    assert all(isinstance(c, ClipInfo) for c in clips)
    assert clips[0].size_bytes == 200


def test_list_clips_on_missing_dir_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    assert list_clips(missing) == []


def test_cleanup_removes_files_older_than_retain_days(tmp_path: Path) -> None:
    day = 86400
    make_clip(tmp_path, "keep.mp4", 10, age_seconds=1 * day)
    make_clip(tmp_path, "stale.mp4", 10, age_seconds=8 * day)
    make_clip(tmp_path, "ancient.mp4", 10, age_seconds=30 * day)

    removed = cleanup(tmp_path, retain_days=7, max_total_gb=100.0)

    remaining = {p.name for p in tmp_path.iterdir()}
    assert remaining == {"keep.mp4"}
    assert set(removed) == {"stale.mp4", "ancient.mp4"}


def test_cleanup_enforces_size_limit_deleting_oldest_first(tmp_path: Path) -> None:
    one_mb = 1024 * 1024
    # Total = 4MB; cap at 2.5MB → must delete the two oldest (2MB) to fit.
    make_clip(tmp_path, "a_oldest.mp4", one_mb, age_seconds=400)
    make_clip(tmp_path, "b.mp4", one_mb, age_seconds=300)
    make_clip(tmp_path, "c.mp4", one_mb, age_seconds=200)
    make_clip(tmp_path, "d_newest.mp4", one_mb, age_seconds=100)

    cap_gb = 2.5 * one_mb / (1024**3)
    removed = cleanup(tmp_path, retain_days=365, max_total_gb=cap_gb)

    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert remaining == ["c.mp4", "d_newest.mp4"]
    assert set(removed) == {"a_oldest.mp4", "b.mp4"}


def test_cleanup_noop_when_under_limits(tmp_path: Path) -> None:
    make_clip(tmp_path, "fresh.mp4", 1000, age_seconds=60)

    removed = cleanup(tmp_path, retain_days=7, max_total_gb=100.0)

    assert removed == []
    assert (tmp_path / "fresh.mp4").exists()
