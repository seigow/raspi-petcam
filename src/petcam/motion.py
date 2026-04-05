"""Frame-difference motion detection.

`MotionDetector.update(frame)` compares against the previous frame using
`cv2.absdiff` and reports True when a contour exceeds `min_area`. After a
trigger, further detections are suppressed for `cooldown_sec`.
"""

from __future__ import annotations

import time
from typing import Callable

import cv2
import numpy as np


class MotionDetector:
    def __init__(
        self,
        threshold: int,
        min_area: int,
        cooldown_sec: float,
        blur_ksize: int = 21,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = threshold
        self.min_area = min_area
        self.cooldown_sec = cooldown_sec
        self.blur_ksize = blur_ksize
        self._clock = clock
        self._prev: np.ndarray | None = None
        self._last_trigger: float | None = None

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(frame, (self.blur_ksize, self.blur_ksize), 0)

    def update(self, frame: np.ndarray) -> bool:
        """Feed the next frame; return True iff motion was detected."""
        current = self._preprocess(frame)

        if self._prev is None:
            self._prev = current
            return False

        delta = cv2.absdiff(self._prev, current)
        _, thresh = cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self._prev = current

        triggered = any(cv2.contourArea(c) >= self.min_area for c in contours)
        if not triggered:
            return False

        now = self._clock()
        if self._last_trigger is not None and (now - self._last_trigger) < self.cooldown_sec:
            return False

        self._last_trigger = now
        return True
