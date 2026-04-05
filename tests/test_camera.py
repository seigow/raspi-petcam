import numpy as np

from petcam.camera import MockCamera


def test_mock_camera_produces_frames_of_configured_size() -> None:
    cam = MockCamera(width=320, height=240)
    cam.start()
    try:
        frame = cam.read_frame()
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (240, 320, 3)
        assert frame.dtype == np.uint8
    finally:
        cam.stop()


def test_mock_camera_read_jpeg_returns_valid_jpeg() -> None:
    cam = MockCamera(width=320, height=240)
    cam.start()
    try:
        blob = cam.read_jpeg()
        assert isinstance(blob, bytes)
        # JPEG SOI marker
        assert blob[:2] == b"\xff\xd8"
        # JPEG EOI marker
        assert blob[-2:] == b"\xff\xd9"
    finally:
        cam.stop()


def test_mock_camera_frames_vary_over_time() -> None:
    """Consecutive frames should differ, so motion detection has something to see."""
    cam = MockCamera(width=320, height=240)
    cam.start()
    try:
        f1 = cam.read_frame()
        f2 = cam.read_frame()
        assert not np.array_equal(f1, f2)
    finally:
        cam.stop()
