import numpy as np

from petcam.motion import MotionDetector


def make_frame(fill: int = 0, shape: tuple[int, int] = (240, 320)) -> np.ndarray:
    return np.full(shape, fill, dtype=np.uint8)


def add_block(frame: np.ndarray, x: int, y: int, w: int, h: int, value: int = 255) -> np.ndarray:
    out = frame.copy()
    out[y : y + h, x : x + w] = value
    return out


def test_no_motion_on_first_frame() -> None:
    det = MotionDetector(threshold=25, min_area=100, cooldown_sec=0.0)
    assert det.update(make_frame()) is False


def test_detects_motion_on_large_change() -> None:
    det = MotionDetector(threshold=25, min_area=100, cooldown_sec=0.0)
    base = make_frame()
    det.update(base)
    # 80x80 white block = 6400 px² of difference, well above min_area=100.
    moved = add_block(base, x=50, y=50, w=80, h=80, value=255)
    assert det.update(moved) is True


def test_ignores_small_change_below_min_area() -> None:
    det = MotionDetector(threshold=25, min_area=5000, cooldown_sec=0.0)
    base = make_frame()
    det.update(base)
    # 10x10 block = 100 px² — below min_area threshold.
    tiny = add_block(base, x=10, y=10, w=10, h=10, value=255)
    assert det.update(tiny) is False


def test_cooldown_suppresses_repeated_triggers() -> None:
    # Use a fake clock so the test is deterministic.
    t = {"now": 1000.0}
    det = MotionDetector(
        threshold=25, min_area=100, cooldown_sec=5.0, clock=lambda: t["now"]
    )
    base = make_frame()
    det.update(base)
    moved = add_block(base, x=50, y=50, w=80, h=80)

    # First motion: triggers.
    assert det.update(moved) is True  # prev is now `moved`

    # Still in cooldown window: motion present but suppressed.
    t["now"] = 1003.0
    assert det.update(base) is False  # big diff vs `moved`, but suppressed
    # prev is now `base`

    # Past cooldown: triggers again on a big change.
    t["now"] = 1020.0
    assert det.update(moved) is True  # big diff vs `base`, cooldown lifted
