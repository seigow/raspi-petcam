from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from petcam.app import create_app
from petcam.camera import MockCamera


@pytest.fixture()
def recordings_dir(tmp_path: Path) -> Path:
    d = tmp_path / "recordings"
    d.mkdir()
    # Two fake clips with distinct sizes.
    (d / "20260101_120000.mp4").write_bytes(b"\x00" * 100)
    (d / "20260102_120000.mp4").write_bytes(b"\x00" * 200)
    return d


@pytest.fixture()
def client(recordings_dir: Path):
    app = create_app(camera=MockCamera(width=160, height=120), recordings_dir=recordings_dir)
    with TestClient(app) as c:
        yield c


def test_status_endpoint_reports_camera_and_storage(client: TestClient) -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["camera"]["running"] is True
    assert body["camera"]["width"] == 160
    assert body["camera"]["height"] == 120
    assert body["storage"]["clip_count"] == 2
    assert body["storage"]["total_bytes"] == 300


def test_list_clips_returns_both(client: TestClient) -> None:
    r = client.get("/api/clips")
    assert r.status_code == 200
    clips = r.json()
    assert len(clips) == 2
    names = {c["filename"] for c in clips}
    assert names == {"20260101_120000.mp4", "20260102_120000.mp4"}
    # Newest first.
    assert clips[0]["filename"] == "20260102_120000.mp4"


def test_get_clip_returns_file_bytes(client: TestClient) -> None:
    r = client.get("/api/clips/20260101_120000.mp4")
    assert r.status_code == 200
    assert r.headers["content-type"] == "video/mp4"
    assert len(r.content) == 100


def test_get_clip_rejects_path_traversal(client: TestClient) -> None:
    r = client.get("/api/clips/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code in (400, 404)


def test_get_missing_clip_returns_404(client: TestClient) -> None:
    r = client.get("/api/clips/nope.mp4")
    assert r.status_code == 404


def test_delete_clip_removes_file(client: TestClient, recordings_dir: Path) -> None:
    r = client.delete("/api/clips/20260101_120000.mp4")
    assert r.status_code == 204
    assert not (recordings_dir / "20260101_120000.mp4").exists()
    assert (recordings_dir / "20260102_120000.mp4").exists()


def test_delete_missing_clip_returns_404(client: TestClient) -> None:
    r = client.delete("/api/clips/nope.mp4")
    assert r.status_code == 404


def test_stream_route_is_registered(client: TestClient) -> None:
    # End-to-end streaming is verified in test_streaming.py; here we just
    # confirm the route is wired into the app (TestClient can't consume an
    # infinite stream cleanly).
    routes = {r.path for r in client.app.routes}  # type: ignore[attr-defined]
    assert "/stream.mjpg" in routes
