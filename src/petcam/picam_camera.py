"""picamera2-backed camera implementation.

Imported lazily at runtime — picamera2 is only available on Raspberry Pi OS,
installed via `apt install python3-picamera2` and exposed to this venv via
`--system-site-packages` (see README).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class Picam2Camera:
    def __init__(self, width: int, height: int, framerate: int, jpeg_quality: int = 80) -> None:
        # Lazy import — non-Pi hosts must be able to import this package.
        from picamera2 import Picamera2

        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self._picam2 = Picamera2()
        config = self._picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": framerate},
        )
        self._picam2.configure(config)
        self._encoder = None

    def start(self) -> None:
        self._picam2.start()
        self._started = True

    def stop(self) -> None:
        self.stop_recording()
        self._picam2.stop()
        self._started = False

    def read_frame(self) -> np.ndarray:
        # Returns RGB888 HxWx3 uint8.
        return self._picam2.capture_array("main")

    def read_jpeg(self) -> bytes:
        rgb = self.read_frame()
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(
            ".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            raise RuntimeError("JPEG encoding failed")
        return buf.tobytes()

    def start_recording(self, path: Path) -> None:
        from picamera2.encoders import H264Encoder
        from picamera2.outputs import FfmpegOutput

        if self._encoder is not None:
            return
        self._encoder = H264Encoder(bitrate=2_000_000)
        output = FfmpegOutput(str(path))
        self._picam2.start_encoder(self._encoder, output)

    def stop_recording(self) -> None:
        if self._encoder is None:
            return
        self._picam2.stop_encoder()
        self._encoder = None
