"""Configuration loading for petcam.

Reads a YAML file into a tree of dataclasses. Every section has defaults so a
minimal config file still produces a fully-populated Config object.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CameraConfig:
    width: int = 1280
    height: int = 720
    framerate: int = 15

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)


@dataclass
class MotionConfig:
    enabled: bool = True
    threshold: int = 25
    min_area: int = 5000
    cooldown_sec: int = 10


@dataclass
class RecordingConfig:
    output_dir: Path = field(default_factory=lambda: Path("./recordings"))
    segment_sec: int = 60
    pre_buffer_sec: int = 3


@dataclass
class StorageConfig:
    max_total_gb: float = 10.0
    retain_days: int = 7


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class Config:
    camera: CameraConfig = field(default_factory=CameraConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


def _build_section(cls: type, data: dict[str, Any] | None) -> Any:
    """Instantiate a dataclass, applying only keys that match its fields."""
    if data is None:
        return cls()
    known = {f.name for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key not in known:
            continue
        # Resolve Path fields from strings.
        field_type = next(f.type for f in fields(cls) if f.name == key)
        if field_type in ("Path", Path) or field_type == "pathlib.Path":
            value = Path(value)
        kwargs[key] = value
    return cls(**kwargs)


def load_config(path: str | Path) -> Config:
    """Load a Config from a YAML file path."""
    raw = yaml.safe_load(Path(path).read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"config must be a mapping, got {type(raw).__name__}")

    sections = {
        "camera": CameraConfig,
        "motion": MotionConfig,
        "recording": RecordingConfig,
        "storage": StorageConfig,
        "server": ServerConfig,
    }
    kwargs = {name: _build_section(cls, raw.get(name)) for name, cls in sections.items()}

    cfg = Config(**kwargs)
    assert is_dataclass(cfg)
    return cfg
