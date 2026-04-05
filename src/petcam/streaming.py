"""MJPEG streaming helpers.

`mjpeg_generator` yields the `multipart/x-mixed-replace` payload frame by
frame. Clients render it directly with `<img src="/stream.mjpg">`.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from .camera import CameraProtocol

BOUNDARY = "frame"
CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={BOUNDARY}"


async def mjpeg_generator(
    camera: CameraProtocol, fps: int = 15
) -> AsyncIterator[bytes]:
    """Yield MJPEG multipart chunks until the client disconnects."""
    delay = 1.0 / max(1, fps)
    while True:
        # Camera read is blocking/CPU-bound; run in a thread to avoid stalling.
        jpeg = await asyncio.to_thread(camera.read_jpeg)
        yield (
            f"--{BOUNDARY}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg)}\r\n\r\n"
        ).encode("ascii") + jpeg + b"\r\n"
        await asyncio.sleep(delay)
