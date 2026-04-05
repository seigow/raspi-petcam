"""Entrypoint that wires the full stack together.

Loads config, selects a camera implementation (real picamera2 or mock), builds
the motion detector + recorder + cleanup tasks, and runs the FastAPI app under
uvicorn.

Run with:
    uv run python -m petcam.main
    # or to skip the real camera:
    PETCAM_MOCK=1 uv run python -m petcam.main
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn

from .app import create_app
from .camera import CameraProtocol
from .config import Config, load_config
from .motion import MotionDetector
from .recorder import MotionRecorder

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config.yaml"
WEB_DIR = REPO_ROOT / "web"


def _build_camera(cfg: Config) -> CameraProtocol:
    if os.environ.get("PETCAM_MOCK"):
        from .camera import MockCamera

        return MockCamera(
            width=cfg.camera.width,
            height=cfg.camera.height,
        )
    from .picam_camera import Picam2Camera

    return Picam2Camera(
        width=cfg.camera.width,
        height=cfg.camera.height,
        framerate=cfg.camera.framerate,
    )


def build_app(config_path: Path = DEFAULT_CONFIG):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = load_config(config_path) if config_path.exists() else Config()
    camera = _build_camera(cfg)

    detector: MotionDetector | None = None
    recorder: MotionRecorder | None = None
    if cfg.motion.enabled:
        detector = MotionDetector(
            threshold=cfg.motion.threshold,
            min_area=cfg.motion.min_area,
            cooldown_sec=cfg.motion.cooldown_sec,
        )
        recorder = MotionRecorder(
            output_dir=cfg.recording.output_dir,
            segment_sec=cfg.recording.segment_sec,
            start_fn=camera.start_recording,
            stop_fn=lambda _path: camera.stop_recording(),
        )

    return cfg, create_app(
        camera=camera,
        recordings_dir=cfg.recording.output_dir,
        motion_detector=detector,
        recorder=recorder,
        motion_fps=5,
        retain_days=cfg.storage.retain_days,
        max_total_gb=cfg.storage.max_total_gb,
        web_dir=WEB_DIR,
    )


def main() -> None:
    cfg, app = build_app()
    uvicorn.run(app, host=cfg.server.host, port=cfg.server.port, log_config=None)


if __name__ == "__main__":
    main()
