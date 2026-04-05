from pathlib import Path
from textwrap import dedent

from petcam.config import Config, load_config


def write_yaml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(dedent(body))
    return path


def test_load_full_config(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
        camera:
          width: 1280
          height: 720
          framerate: 15
        motion:
          enabled: true
          threshold: 25
          min_area: 5000
          cooldown_sec: 10
        recording:
          output_dir: ./recordings
          segment_sec: 60
          pre_buffer_sec: 3
        storage:
          max_total_gb: 10
          retain_days: 7
        server:
          host: 0.0.0.0
          port: 8000
        """,
    )

    cfg = load_config(path)

    assert isinstance(cfg, Config)
    assert cfg.camera.width == 1280
    assert cfg.camera.height == 720
    assert cfg.camera.framerate == 15
    assert cfg.motion.enabled is True
    assert cfg.motion.threshold == 25
    assert cfg.motion.min_area == 5000
    assert cfg.motion.cooldown_sec == 10
    assert cfg.recording.output_dir == Path("./recordings")
    assert cfg.recording.segment_sec == 60
    assert cfg.recording.pre_buffer_sec == 3
    assert cfg.storage.max_total_gb == 10
    assert cfg.storage.retain_days == 7
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 8000


def test_defaults_when_sections_missing(tmp_path: Path) -> None:
    # Empty config file — every section falls back to defaults.
    path = write_yaml(tmp_path, "{}")

    cfg = load_config(path)

    assert cfg.camera.width == 1280
    assert cfg.camera.height == 720
    assert cfg.camera.framerate == 15
    assert cfg.motion.enabled is True
    assert cfg.recording.segment_sec == 60
    assert cfg.storage.retain_days == 7
    assert cfg.server.port == 8000


def test_partial_override(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
        camera:
          framerate: 30
        server:
          port: 9000
        """,
    )

    cfg = load_config(path)

    # Overridden values.
    assert cfg.camera.framerate == 30
    assert cfg.server.port == 9000
    # Untouched values stay at defaults.
    assert cfg.camera.width == 1280
    assert cfg.server.host == "0.0.0.0"
    assert cfg.motion.threshold == 25


def test_resolution_property(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, "{}")
    cfg = load_config(path)
    assert cfg.camera.resolution == (1280, 720)
