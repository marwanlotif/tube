import shutil
from pathlib import Path

import pytest

import app.domain.urls as urls_module
from app.core.config import Config

FAKES = Path(__file__).parent / "fakes"
FAKE_YTDLP = FAKES / "yt-dlp"


def pytest_configure() -> None:
    FAKE_YTDLP.chmod(0o755)


@pytest.fixture
def media_roots(tmp_path: Path) -> Path:
    root = tmp_path / "media"
    for name in ("Videos", "Music", "Downloads"):
        (root / name).mkdir(parents=True)
    return root


@pytest.fixture
def config(tmp_path: Path, media_roots: Path) -> Config:
    return Config(
        data_dir=tmp_path / "data",
        allowed_media_roots=":".join(
            str(media_roots / name) for name in ("Videos", "Music", "Downloads")
        ),
        ytdlp_path=str(FAKE_YTDLP),
        ffmpeg_path=shutil.which("ffmpeg") or "/bin/true",
        max_concurrent_downloads=2,
        open_browser=False,
    )


@pytest.fixture
def fake_env(monkeypatch):
    monkeypatch.setenv("FAKE_YTDLP_INFO", str(FAKES / "info.json"))
    monkeypatch.setenv("FAKE_YTDLP_PLAYLIST_INFO", str(FAKES / "playlist.json"))
    monkeypatch.setenv("FAKE_YTDLP_CHANNEL_INFO", str(FAKES / "channel.json"))
    monkeypatch.setenv("FAKE_DELAY", "0")
    monkeypatch.delenv("FAKE_NO_OUTPUT", raising=False)
    monkeypatch.delenv("FAKE_EXIT", raising=False)
    return monkeypatch


@pytest.fixture
def client(config, fake_env, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(urls_module, "assert_public_host", lambda *args, **kwargs: None)
    app = create_app(config)
    with TestClient(app) as test_client:
        test_client.headers["X-Vid-Dwn-Token"] = app.state.token
        yield test_client
