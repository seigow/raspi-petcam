"""Camera abstraction.

`CameraProtocol` is what the rest of the app depends on. `MockCamera` is the
test/dev implementation (synthetic moving frames). The real picamera2-backed
implementation lives in `petcam.picam_camera` and is imported conditionally at
runtime so the package remains importable on non-Pi hosts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class CameraProtocol(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def read_frame(self) -> np.ndarray:
        """Return the latest frame as an HxWx3 uint8 ndarray."""
        ...

    def read_jpeg(self) -> bytes:
        """Return the latest frame JPEG-encoded."""
        ...

    def start_recording(self, path: Path) -> None: ...
    def stop_recording(self) -> None: ...


class MockCamera:
    """Synthetic camera that draws a moving rectangle on a noise background."""

    def __init__(self, width: int = 1280, height: int = 720, jpeg_quality: int = 80) -> None:
        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self._tick = 0
        self._started = False
        self._rng = np.random.default_rng(42)

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def _render(self) -> np.ndarray:
        # Low-variance noise so JPEG stays small but frames are never identical.
        frame = self._rng.integers(0, 32, size=(self.height, self.width, 3), dtype=np.uint8)
        # Moving white rectangle — position depends on tick.
        box_w, box_h = 80, 80
        x = (self._tick * 7) % max(1, self.width - box_w)
        y = (self._tick * 5) % max(1, self.height - box_h)
        frame[y : y + box_h, x : x + box_w] = 255
        self._tick += 1
        return frame

    def read_frame(self) -> np.ndarray:
        if not self._started:
            raise RuntimeError("camera not started")
        return self._render()

    def read_jpeg(self) -> bytes:
        frame = self.read_frame()
        ok, buf = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        return buf.tobytes()

    def start_recording(self, path: Path) -> None:
        # Dev-mode: drop a placeholder file so the API can list it.
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"MOCK")

    def stop_recording(self) -> None:
        return None
