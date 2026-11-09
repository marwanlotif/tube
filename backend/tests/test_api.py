import os
import shutil
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.domain.urls as urls_module
from app.core.config import Config
from app.main import create_app

INFO_URL = "https://example.com/watch?v=abc123"


def make_client(config: Config, monkeypatch) -> TestClient:
    monkeypatch.setattr(urls_module, "assert_public_host", lambda *args, **kwargs: None)
    app = create_app(config)
    client = TestClient(app)
    client.headers["X-Vid-Dwn-Token"] = app.state.token
    return client


def wait_for_status(client: TestClient, download_id: str, wanted: set[str], timeout: float = 15):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        response = client.get(f"/api/downloads/{download_id}")
        assert response.status_code == 200, response.text
        last = response.json()
        if last["status"] in wanted:
            return last
        time.sleep(0.05)
    raise AssertionError(f"timeout waiting for {wanted}; last={last}")


def start_download(client: TestClient, preset: str = "best_1080") -> dict:
    response = client.post(
        "/api/downloads", json={"url": INFO_URL, "preset": preset}
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_video_info_returns_formats_and_presets(client):
    response = client.post("/api/videos/info", json={"url": INFO_URL})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Test Video"
    assert any(f["format_id"] == "137" for f in body["formats"])
    best = next(p for p in body["presets"] if p["key"] == "best_1080")
    assert best["container"] == "mp4"
    assert best["requires_merge"] is True


def test_missing_token_is_rejected(client):
    del client.headers["X-Vid-Dwn-Token"]
    response = client.post("/api/videos/info", json={"url": INFO_URL})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_websocket_rejects_unknown_origin(client):
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(
        "/api/ws", headers={"origin": "http://evil.example"}
    ):
        pass
    assert exc.value.code == 4403


def test_websocket_requires_valid_token_and_sends_snapshot(client):
    with client.websocket_connect("/api/ws") as socket:
        socket.send_json({"type": "auth", "token": "wrong"})
        with pytest.raises(WebSocketDisconnect) as exc:
            socket.receive_json()
    assert exc.value.code == 4401

    with client.websocket_connect("/api/ws") as socket:
        socket.send_json({"type": "auth", "token": client.app.state.token})
        message = socket.receive_json()
    assert message["type"] == "snapshot"
    assert isinstance(message["downloads"], list)


def test_missing_ffmpeg_is_reported_and_blocks_merge(config, fake_env, monkeypatch):
    real_which = shutil.which
    monkeypatch.setattr(
        "app.integrations.ytdlp.shutil.which",
        lambda name: None if name == "ffmpeg" else real_which(name),
    )
    config.ffmpeg_path = None
    with make_client(config, monkeypatch) as client:
        assert client.get("/api/system").json()["ffmpeg_ok"] is False
        client.post("/api/videos/info", json={"url": INFO_URL})
        response = client.post(
            "/api/downloads", json={"url": INFO_URL, "preset": "best_1080"}
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "FFMPEG_MISSING"


def test_download_completes_and_verifies_file(client, config):
    client.post("/api/videos/info", json={"url": INFO_URL})
    created = start_download(client)
    assert created["status"] in {"queued", "downloading"}
    done = wait_for_status(client, created["id"], {"completed", "failed"})
    assert done["status"] == "completed", done
    assert done["format_selector"] == "137+140"
    assert done["container"] == "mp4"
    assert done["progress"] == 100
    assert done["output_path"].endswith("video.mp4")
    assert os.path.getsize(done["output_path"]) > 0
    assert done["file_size"] > 0


def test_audio_download_uses_audio_dir(client):
    client.post("/api/videos/info", json={"url": INFO_URL})
    response = client.post(
        "/api/downloads", json={"url": INFO_URL, "mode": "audio", "audio_format": "mp3"}
    )
    assert response.status_code == 202, response.text
    done = wait_for_status(client, response.json()["id"], {"completed", "failed"})
    assert done["status"] == "completed", done
    assert done["container"] == "mp3"


def test_missing_output_is_never_completed(client, monkeypatch):
    monkeypatch.setenv("FAKE_NO_OUTPUT", "1")
    client.post("/api/videos/info", json={"url": INFO_URL})
    created = start_download(client)
    done = wait_for_status(client, created["id"], {"completed", "failed"})
    assert done["status"] == "failed"
    assert done["error_code"] == "OUTPUT_MISSING"


def test_failed_process_surfaces_stderr(client, monkeypatch):
    monkeypatch.setenv("FAKE_EXIT", "5")
    client.post("/api/videos/info", json={"url": INFO_URL})
    created = start_download(client)
    done = wait_for_status(client, created["id"], {"failed"})
    assert done["error_code"] == "DOWNLOAD_FAILED"
    assert "fake failure" in done["error_message"]


def test_cancel_running_download_is_idempotent(config, monkeypatch, fake_env):
    monkeypatch.setenv("FAKE_DELAY", "30")
    with make_client(config, monkeypatch) as client:
        client.post("/api/videos/info", json={"url": INFO_URL})
        created = start_download(client)
        wait_for_status(client, created["id"], {"downloading"})
        first = client.post(f"/api/downloads/{created['id']}/cancel")
        assert first.status_code == 200
        second = client.post(f"/api/downloads/{created['id']}/cancel")
        assert second.status_code == 200
        assert first.json()["status"] == "canceled"
        assert second.json()["status"] == "canceled"


def test_retry_after_cancel(client, monkeypatch):
    monkeypatch.setenv("FAKE_DELAY", "30")
    client.post("/api/videos/info", json={"url": INFO_URL})
    created = start_download(client)
    wait_for_status(client, created["id"], {"downloading"})
    client.post(f"/api/downloads/{created['id']}/cancel")
    monkeypatch.setenv("FAKE_DELAY", "0")
    retried = client.post(f"/api/downloads/{created['id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["attempts"] == 1
    done = wait_for_status(client, created["id"], {"completed", "failed"})
    assert done["status"] == "completed", done


def test_invalid_url_is_rejected(client):
    response = client.post("/api/videos/info", json={"url": "file:///etc/passwd"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_URL"


def test_settings_roundtrip_and_path_guard(client, media_roots):
    current = client.get("/api/settings").json()
    current["filename_template"] = "%(uploader)s - %(title)s.%(ext)s"
    current["network"]["fragments"] = 8
    updated = client.put("/api/settings", json=current)
    assert updated.status_code == 200, updated.text
    assert updated.json()["network"]["fragments"] == 8
    fetched = client.get("/api/settings").json()
    assert fetched["filename_template"] == current["filename_template"]

    bad = dict(fetched)
    bad["video_dir"] = "/etc"
    response = client.put("/api/settings", json=bad)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PATH"


def test_stats_and_system(client):
    assert client.get("/api/system").json()["ytdlp_ok"] is True
    stats = client.get("/api/stats").json()
    assert "disk_free" in stats and stats["disk_free"] > 0


def _info_calls(log_path) -> list[str]:
    if not log_path.exists():
        return []
    return [line for line in log_path.read_text().splitlines() if " -J " in f" {line} "]


def test_info_extraction_uses_browser_cookies_from_settings(client, fake_env, tmp_path):
    log_path = tmp_path / "argv.log"
    fake_env.setenv("FAKE_ARGV_LOG", str(log_path))

    assert client.post("/api/videos/info", json={"url": INFO_URL}).status_code == 200
    assert "--cookies-from-browser" not in _info_calls(log_path)[-1]

    settings = client.get("/api/settings").json()
    settings["cookies_from_browser"] = "firefox"
    assert client.put("/api/settings", json=settings).status_code == 200

    # A different cookie source must not be served from the anonymous cache entry.
    assert client.post("/api/videos/info", json={"url": INFO_URL}).status_code == 200
    calls = _info_calls(log_path)
    assert len(calls) == 2
    assert "--cookies-from-browser firefox" in calls[-1]
