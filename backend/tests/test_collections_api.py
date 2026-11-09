import pytest
from fastapi.testclient import TestClient

import app.domain.urls as urls_module
from app.domain.urls import looks_like_playlist_member
from app.main import create_app

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLtest123"
CHANNEL_URL = "https://www.youtube.com/@tester"
MIXED_URL = "https://www.youtube.com/watch?v=abc123&list=PLtest123"
SHORT_MIXED_URL = "https://youtu.be/abc123?list=PLtest123"
VIDEO_URL = "https://example.com/watch?v=abc123"


def _probes(log_path) -> list[str]:
    if not log_path.exists():
        return []
    return [line for line in log_path.read_text().splitlines() if " -J " in f" {line} "]


def info(client, url, **extra):
    return client.post("/api/videos/info", json={"url": url, **extra})


def test_playlist_link_returns_a_collection_listing(client):
    response = info(client, PLAYLIST_URL)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["kind"] == "collection"
    assert body["collection_type"] == "playlist"
    assert body["title"] == "Test Playlist"
    assert body["total"] == 8
    assert body["truncated"] is False
    assert body["max_entries"] == 500
    entries = {e["id"]: e for e in body["entries"]}
    assert list(entries) == ["vid001", "vid002", "vidpriv", "vidsoon", "local", "vid003"]
    assert entries["vid002"] == {
        "id": "vid002",
        "index": 2,
        "title": "Second Video",
        "url": "https://www.youtube.com/watch?v=vid002",
        "duration_s": 125,
        "kind": "video",
        "available": True,
        "reason": None,
    }
    assert entries["vidpriv"]["available"] is False
    availability = {p["key"]: p["available"] for p in body["presets"]}
    assert {"best_1080", "audio"} <= set(availability)
    assert [key for key, ok in availability.items() if not ok] == ["webm_1080"]


def test_channel_link_lists_its_tabs_as_nested_collections(client):
    body = info(client, CHANNEL_URL).json()
    assert body["kind"] == "collection"
    assert body["collection_type"] == "channel"
    assert [(e["kind"], e["title"]) for e in body["entries"]] == [
        ("collection", "Tester - Videos"),
        ("collection", "Tester - Shorts"),
        ("collection", "Test Playlist"),
    ]


def test_single_video_keeps_its_response_shape(client):
    body = info(client, VIDEO_URL).json()
    assert body["kind"] == "video"
    assert body["playlist_hint"] is False
    assert body["formats"] and body["presets"]


@pytest.mark.parametrize("url", [MIXED_URL, SHORT_MIXED_URL])
def test_link_to_video_inside_playlist_prefers_the_video_but_hints(client, url):
    video = info(client, url).json()
    assert video["kind"] == "video"
    assert video["playlist_hint"] is True

    listing = info(client, url, playlist=True).json()
    assert listing["kind"] == "collection"
    assert listing["title"] == "Test Playlist"


def test_probe_uses_a_flat_capped_listing(client, fake_env, tmp_path):
    log_path = tmp_path / "argv.log"
    fake_env.setenv("FAKE_ARGV_LOG", str(log_path))

    info(client, MIXED_URL)
    info(client, MIXED_URL, playlist=True)
    first, second = _probes(log_path)
    for argv in (first, second):
        assert "--flat-playlist" in argv
        assert "--playlist-items 1:500" in argv
    assert "--no-playlist" in first and "--yes-playlist" not in first
    assert "--yes-playlist" in second and "--no-playlist" not in second


def test_collection_listing_is_cached_for_the_explicit_playlist_request(
    client, fake_env, tmp_path
):
    log_path = tmp_path / "argv.log"
    fake_env.setenv("FAKE_ARGV_LOG", str(log_path))

    assert info(client, PLAYLIST_URL).json()["kind"] == "collection"
    assert info(client, PLAYLIST_URL).json()["kind"] == "collection"
    assert info(client, PLAYLIST_URL, playlist=True).json()["kind"] == "collection"
    assert len(_probes(log_path)) == 1


def test_listing_is_truncated_at_the_configured_cap(config, fake_env, monkeypatch):
    monkeypatch.setattr(urls_module, "assert_public_host", lambda *args, **kwargs: None)
    capped = config.model_copy(update={"max_collection_entries": 3})
    app = create_app(capped)
    with TestClient(app) as client:
        client.headers["X-Vid-Dwn-Token"] = app.state.token
        body = info(client, PLAYLIST_URL).json()
    assert body["truncated"] is True
    assert body["max_entries"] == 3
    assert [e["id"] for e in body["entries"]] == ["vid001", "vid002"]  # 3rd is a duplicate


def test_single_download_endpoint_rejects_collection_links(client):
    response = client.post("/api/downloads", json={"url": PLAYLIST_URL, "preset": "best_1080"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IS_COLLECTION"


def test_empty_listing_is_reported(client, fake_env, tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text('{"_type": "playlist", "id": "PLempty", "entries": []}')
    fake_env.setenv("FAKE_YTDLP_PLAYLIST_INFO", str(empty))
    response = info(client, "https://www.youtube.com/playlist?list=PLempty")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_ENTRIES"


def test_playlist_hint_only_for_links_naming_both():
    assert looks_like_playlist_member(MIXED_URL)
    assert looks_like_playlist_member(SHORT_MIXED_URL)
    assert not looks_like_playlist_member("https://youtu.be/abc123")
    assert not looks_like_playlist_member("https://youtu.be/?list=PLtest123")
    assert not looks_like_playlist_member("https://example.com/abc123?list=PLtest123")
    assert not looks_like_playlist_member(PLAYLIST_URL)
    assert not looks_like_playlist_member(VIDEO_URL)
    assert not looks_like_playlist_member("https://x.test/watch?v=a&list=")
