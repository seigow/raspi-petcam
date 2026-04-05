import asyncio

from petcam.camera import MockCamera
from petcam.streaming import BOUNDARY, mjpeg_generator


def test_mjpeg_generator_yields_multipart_chunks() -> None:
    cam = MockCamera(width=160, height=120)
    cam.start()

    async def collect_n(n: int) -> list[bytes]:
        chunks: list[bytes] = []
        agen = mjpeg_generator(cam, fps=60)
        try:
            async for chunk in agen:
                chunks.append(chunk)
                if len(chunks) >= n:
                    break
        finally:
            await agen.aclose()
            cam.stop()
        return chunks

    chunks = asyncio.run(collect_n(2))

    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.startswith(f"--{BOUNDARY}\r\n".encode())
        assert b"Content-Type: image/jpeg" in chunk
        assert b"Content-Length:" in chunk
        # JPEG SOI appears after the headers.
        assert b"\xff\xd8" in chunk
        # Each chunk ends with the trailing CRLF before the next boundary.
        assert chunk.endswith(b"\r\n")
