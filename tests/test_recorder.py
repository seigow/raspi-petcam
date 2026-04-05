from pathlib import Path

from petcam.recorder import MotionRecorder


def test_motion_starts_clip_with_timestamped_filename(tmp_path: Path) -> None:
    started: list[Path] = []
    stopped: list[Path] = []
    t = {"now": 1000.0}
    rec = MotionRecorder(
        output_dir=tmp_path,
        segment_sec=60,
        start_fn=started.append,
        stop_fn=stopped.append,
        clock=lambda: t["now"],
        timestamp_fn=lambda: "20260405_120000",
    )

    rec.on_motion()

    assert len(started) == 1
    assert started[0] == tmp_path / "20260405_120000.mp4"
    assert stopped == []
    assert rec.is_recording() is True


def test_second_motion_does_not_restart_clip(tmp_path: Path) -> None:
    started: list[Path] = []
    stopped: list[Path] = []
    t = {"now": 0.0}
    rec = MotionRecorder(
        output_dir=tmp_path,
        segment_sec=60,
        start_fn=started.append,
        stop_fn=stopped.append,
        clock=lambda: t["now"],
        timestamp_fn=lambda: "ts",
    )

    rec.on_motion()
    t["now"] = 10.0
    rec.on_motion()

    assert len(started) == 1
    assert stopped == []


def test_tick_stops_clip_after_segment_sec(tmp_path: Path) -> None:
    started: list[Path] = []
    stopped: list[Path] = []
    t = {"now": 0.0}
    rec = MotionRecorder(
        output_dir=tmp_path,
        segment_sec=30,
        start_fn=started.append,
        stop_fn=stopped.append,
        clock=lambda: t["now"],
        timestamp_fn=lambda: "ts",
    )

    rec.on_motion()

    t["now"] = 29.0
    rec.tick()
    assert rec.is_recording() is True
    assert stopped == []

    t["now"] = 31.0
    rec.tick()
    assert rec.is_recording() is False
    assert stopped == [tmp_path / "ts.mp4"]


def test_motion_during_clip_extends_end_time(tmp_path: Path) -> None:
    started: list[Path] = []
    stopped: list[Path] = []
    t = {"now": 0.0}
    rec = MotionRecorder(
        output_dir=tmp_path,
        segment_sec=30,
        start_fn=started.append,
        stop_fn=stopped.append,
        clock=lambda: t["now"],
        timestamp_fn=lambda: "ts",
    )

    rec.on_motion()

    # New motion at t=20 extends end from 30 to 50.
    t["now"] = 20.0
    rec.on_motion()

    t["now"] = 35.0
    rec.tick()
    assert rec.is_recording() is True  # still within extended window

    t["now"] = 51.0
    rec.tick()
    assert rec.is_recording() is False
    assert len(stopped) == 1
