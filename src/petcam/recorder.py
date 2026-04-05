"""Motion-triggered recording state machine.

`MotionRecorder` decides *when* to start and stop clips; the actual encoding
is delegated to caller-supplied `start_fn(path)` and `stop_fn(path)` hooks so
this module is testable without picamera2.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Callable


def _default_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class MotionRecorder:
    def __init__(
        self,
        output_dir: Path,
        segment_sec: int,
        start_fn: Callable[[Path], None],
        stop_fn: Callable[[Path], None],
        clock: Callable[[], float] = time.monotonic,
        timestamp_fn: Callable[[], str] = _default_timestamp,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.segment_sec = segment_sec
        self._start_fn = start_fn
        self._stop_fn = stop_fn
        self._clock = clock
        self._timestamp_fn = timestamp_fn

        self._current_path: Path | None = None
        self._end_at: float = 0.0

    def is_recording(self) -> bool:
        return self._current_path is not None

    def on_motion(self) -> None:
        """Begin a new clip, or extend the current one's end time."""
        now = self._clock()
        if self._current_path is None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"{self._timestamp_fn()}.mp4"
            self._current_path = path
            self._end_at = now + self.segment_sec
            self._start_fn(path)
        else:
            # Extend end_at so continuous motion stays in one clip.
            self._end_at = max(self._end_at, now + self.segment_sec)

    def tick(self) -> None:
        """Stop the active clip if its window has elapsed."""
        if self._current_path is None:
            return
        if self._clock() >= self._end_at:
            path = self._current_path
            self._current_path = None
            self._stop_fn(path)

    def force_stop(self) -> None:
        """Stop immediately (used at shutdown)."""
        if self._current_path is not None:
            path = self._current_path
            self._current_path = None
            self._stop_fn(path)
