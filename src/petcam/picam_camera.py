"""picamera2-backed camera implementation.

Imported lazily at runtime — picamera2 is only available on Raspberry Pi OS,
installed via `apt install python3-picamera2` and exposed to this venv via
`--system-site-packages` (see README).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .camera import apply_rotation


def _build_transform(rotation: int):
    """Convert rotation degrees to a libcamera Transform.

    Only 0 and 180 are handled via hardware transform (hflip+vflip).
    90/270 require transpose which is not supported by all sensors,
    so those fall back to software rotation in read_frame().
    """
    from libcamera import Transform

    r = rotation % 360
    if r == 180:
        return Transform(hflip=True, vflip=True)
    return Transform()


class Picam2Camera:
    def __init__(self, width: int, height: int, framerate: int, jpeg_quality: int = 80, rotation: int = 0) -> None:
        # Lazy import — non-Pi hosts must be able to import this package.
        from picamera2 import Picamera2

        self.width = width
        self.height = height
        self.jpeg_quality = jpeg_quality
        self._rotation = rotation
        # Hardware handles 0/180; software handles 90/270.
        self._hw_rotated = (rotation % 360) in (0, 180)
        self._picam2 = Picamera2()
        # Use the full sensor area for maximum field of view.
        fw, fh = self._picam2.camera_properties["PixelArraySize"]
        config = self._picam2.create_video_configuration(
            main={"size": (width, height), "format": "RGB888"},
            controls={"FrameRate": framerate, "ScalerCrop": (0, 0, fw, fh)},
            transform=_build_transform(rotation),
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
        # 0/180 are already handled by hardware Transform; only 90/270 need software rotation.
        frame = self._picam2.capture_array("main")
        if not self._hw_rotated:
            frame = apply_rotation(frame, self._rotation)
        return frame

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
