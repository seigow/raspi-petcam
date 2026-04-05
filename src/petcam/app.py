"""FastAPI application factory.

The factory wires a camera implementation and recordings directory into the
HTTP API. Lifespan starts/stops the camera. Kept free of picamera2 imports so
tests can run on any host.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse

from .camera import CameraProtocol
from .motion import MotionDetector
from .recorder import MotionRecorder
from .storage import cleanup, list_clips
from .streaming import CONTENT_TYPE as MJPEG_CONTENT_TYPE
from .streaming import mjpeg_generator

log = logging.getLogger(__name__)


def _resolve_clip(recordings_dir: Path, filename: str) -> Path:
    """Resolve `filename` inside `recordings_dir`, rejecting traversal."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    candidate = (recordings_dir / filename).resolve()
    try:
        candidate.relative_to(recordings_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid filename") from exc
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="clip not found")
    return candidate


def create_app(
    camera: CameraProtocol,
    recordings_dir: Path,
    *,
    motion_detector: MotionDetector | None = None,
    recorder: MotionRecorder | None = None,
    motion_fps: int = 5,
    retain_days: int | None = None,
    max_total_gb: float | None = None,
    cleanup_interval_sec: int = 60,
    web_dir: Path | None = None,
) -> FastAPI:
    recordings_dir = Path(recordings_dir)
    recordings_dir.mkdir(parents=True, exist_ok=True)

    async def motion_loop() -> None:
        delay = 1.0 / max(1, motion_fps)
        while True:
            try:
                frame = await asyncio.to_thread(camera.read_frame)
                if motion_detector is not None and motion_detector.update(frame):
                    if recorder is not None:
                        recorder.on_motion()
                        log.info("motion detected — recording")
                if recorder is not None:
                    recorder.tick()
            except Exception:  # noqa: BLE001 — loop must keep running
                log.exception("motion loop error")
            await asyncio.sleep(delay)

    async def cleanup_loop() -> None:
        while True:
            try:
                if retain_days is not None and max_total_gb is not None:
                    removed = await asyncio.to_thread(
                        cleanup, recordings_dir, retain_days, max_total_gb
                    )
                    if removed:
                        log.info("cleanup removed %d file(s): %s", len(removed), removed)
            except Exception:
                log.exception("cleanup loop error")
            await asyncio.sleep(cleanup_interval_sec)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        camera.start()
        tasks: list[asyncio.Task] = []
        if motion_detector is not None:
            tasks.append(asyncio.create_task(motion_loop()))
        if retain_days is not None and max_total_gb is not None:
            tasks.append(asyncio.create_task(cleanup_loop()))
        try:
            yield
        finally:
            for t in tasks:
                t.cancel()
            if recorder is not None:
                recorder.force_stop()
            camera.stop()

    app = FastAPI(title="petcam", lifespan=lifespan)
    app.state.camera = camera
    app.state.recordings_dir = recordings_dir

    @app.get("/api/status")
    def status() -> dict:
        clips = list_clips(recordings_dir)
        total = sum(c.size_bytes for c in clips)
        # `MockCamera` carries width/height attrs; real cameras should too.
        width = getattr(camera, "width", None)
        height = getattr(camera, "height", None)
        running = getattr(camera, "_started", True)
        return {
            "camera": {"running": bool(running), "width": width, "height": height},
            "storage": {"clip_count": len(clips), "total_bytes": total},
        }

    @app.get("/api/clips")
    def list_clips_endpoint() -> list[dict]:
        return [
            {
                "filename": c.filename,
                "size_bytes": c.size_bytes,
                "created_at": c.created_at.isoformat(),
            }
            for c in list_clips(recordings_dir)
        ]

    @app.get("/api/clips/{filename}")
    def get_clip(filename: str) -> FileResponse:
        path = _resolve_clip(recordings_dir, filename)
        return FileResponse(path, media_type="video/mp4", filename=filename)

    @app.delete("/api/clips/{filename}", status_code=204)
    def delete_clip(filename: str) -> Response:
        path = _resolve_clip(recordings_dir, filename)
        path.unlink()
        return Response(status_code=204)

    @app.get("/stream.mjpg")
    def stream() -> StreamingResponse:
        return StreamingResponse(
            mjpeg_generator(camera), media_type=MJPEG_CONTENT_TYPE
        )

    if web_dir is not None:
        index_path = Path(web_dir) / "index.html"

        @app.get("/")
        def root() -> FileResponse:
            return FileResponse(index_path, media_type="text/html")

    return app
