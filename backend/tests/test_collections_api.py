import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.domain.urls as urls_module
from app.core.errors import AppError
from app.domain.urls import looks_like_playlist_member
from app.main import create_app
from tests.conftest import FAKES

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


# --- queuing and managing collections -------------------------------------------------

ALL_VIDEOS = ["vid001", "vid002", "vid003"]


def queue(client, entry_ids=ALL_VIDEOS, url=PLAYLIST_URL, **extra):
    return client.post("/api/collections", json={"url": url, "entry_ids": entry_ids, **extra})


def wait_until_settled(client, collection_id: str, timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    body = None
    while time.time() < deadline:
        body = client.get(f"/api/collections/{collection_id}").json()
        if body["active_total"] == 0:
            return body
        time.sleep(0.05)
    raise AssertionError(f"collection did not settle: {body}")


def items_of(client, collection_id: str) -> list[dict]:
    response = client.get("/api/downloads", params={"collection_id": collection_id})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_selected_entries_are_queued_in_playlist_order_into_a_folder(client):
    settings = client.get("/api/settings").json()
    response = queue(client, ["vid002", "vid001", "vidpriv", "nope", "vid001"])
    assert response.status_code == 202, response.text
    body = response.json()

    assert body["created"] == 2
    assert body["skipped"] == {
        "not_found": 1, "unavailable": 1, "blocked": 0, "already_downloaded": 0
    }
    collection = body["collection"]
    assert collection["collection_type"] == "playlist"
    assert collection["title"] == "Test Playlist"
    assert collection["preset_key"] == "best_1080"
    assert collection["entry_total"] == collection["item_total"] == 2
    folder = Path(collection["output_dir"])
    assert folder == Path(settings["video_dir"]) / "Test Playlist"
    assert folder.is_dir()

    items = items_of(client, collection["id"])
    assert [(i["video_id"], i["playlist_index"]) for i in items] == [("vid001", 1), ("vid002", 2)]
    assert {i["collection_id"] for i in items} == {collection["id"]}
    assert {i["format_label"] for i in items} == {"Up to 1080p"}

    standalone = client.get("/api/downloads", params={"standalone": True}).json()
    assert standalone["total"] == 0

    settled = wait_until_settled(client, collection["id"])
    assert settled["completed_total"] == 2
    assert settled["progress"] == 100.0
    assert all(i["status"] == "completed" for i in items_of(client, collection["id"]))


def test_playlist_index_is_rendered_into_each_items_template(client):
    settings = client.get("/api/settings").json()
    settings["filename_template"] = "%(playlist_index)02d - %(title)s.%(ext)s"
    assert client.put("/api/settings", json=settings).status_code == 200

    collection = queue(client, ["vid002"]).json()["collection"]
    (item,) = items_of(client, collection["id"])
    row = client.portal.call(client.app.state.repo.get, item["id"])
    assert row.job_spec["filename_template"] == "02 - %(title)s.%(ext)s"
    assert row.job_spec["revalidate"] is True and row.job_spec["selector"] is None


def test_already_downloaded_videos_are_skipped_unless_asked(client):
    first = queue(client).json()["collection"]
    wait_until_settled(client, first["id"])

    again = queue(client)
    assert again.status_code == 422
    error = again.json()["error"]
    assert error["code"] == "NOTHING_TO_DOWNLOAD"
    assert error["details"]["skipped"]["already_downloaded"] == 3

    forced = queue(client, skip_existing=False)
    assert forced.status_code == 202
    assert forced.json()["created"] == 3


def test_videos_still_in_progress_count_as_existing(client, fake_env):
    fake_env.setenv("FAKE_DELAY", "1")
    queue(client, ["vid001"])
    body = queue(client, ["vid001", "vid002"]).json()
    assert body["created"] == 1
    assert body["skipped"]["already_downloaded"] == 1


def test_items_can_go_straight_into_the_download_folder(client):
    settings = client.get("/api/settings").json()
    collection = queue(client, subfolder=False).json()["collection"]
    assert collection["output_dir"] == settings["video_dir"]


def test_audio_collection_uses_the_audio_folder_and_format(client):
    settings = client.get("/api/settings").json()
    body = queue(client, mode="audio", audio_format="opus").json()
    collection = body["collection"]
    assert collection["mode"] == "audio"
    assert collection["preset_key"] == "audio"
    assert Path(collection["output_dir"]).parent == Path(settings["audio_dir"])
    assert {i["container"] for i in items_of(client, collection["id"])} == {"opus"}
    settled = wait_until_settled(client, collection["id"])
    assert settled["completed_total"] == 3


def test_entries_on_private_hosts_are_never_queued(client, fake_env, monkeypatch, tmp_path):
    listing = json.loads((FAKES / "playlist.json").read_text())
    listing["entries"].append(
        {"_type": "url", "ie_key": "Generic", "id": "lan", "title": "Router admin",
         "url": "http://router.internal/admin"}
    )
    path = tmp_path / "with_lan.json"
    path.write_text(json.dumps(listing))
    fake_env.setenv("FAKE_YTDLP_PLAYLIST_INFO", str(path))

    def resolver_check(hostname, *args, **kwargs):
        if hostname == "router.internal":
            raise AppError("INVALID_URL", "Private or local addresses are not allowed")

    monkeypatch.setattr(urls_module, "assert_public_host", resolver_check)
    body = queue(client, ["vid001", "lan"]).json()
    assert body["created"] == 1
    assert body["skipped"]["blocked"] == 1


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"preset": "best_9000"}, "INVALID_PRESET"),
        ({"entry_ids": ["nope"]}, "NOTHING_TO_DOWNLOAD"),
        ({"url": VIDEO_URL}, "NOT_A_COLLECTION"),
        ({"subtitles": True, "subtitle_langs": "en;rm"}, "INVALID_SETTINGS"),
    ],
)
def test_invalid_collection_requests_are_rejected(client, payload, code):
    body = {"url": PLAYLIST_URL, "entry_ids": ALL_VIDEOS, **payload}
    response = client.post("/api/collections", json=body)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == code
    assert client.get("/api/collections").json()["total"] == 0


def test_entry_ids_are_required(client):
    response = client.post("/api/collections", json={"url": PLAYLIST_URL, "entry_ids": []})
    assert response.status_code == 422


def test_collection_endpoints_require_the_token(client):
    collection = queue(client).json()["collection"]
    del client.headers["X-Vid-Dwn-Token"]
    for method, path in (
        ("post", "/api/collections"),
        ("post", f"/api/collections/{collection['id']}/cancel"),
        ("post", f"/api/collections/{collection['id']}/retry"),
        ("delete", f"/api/collections/{collection['id']}"),
    ):
        response = getattr(client, method)(path)
        assert response.status_code == 403, (method, path)
        assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_cancel_then_retry_a_whole_collection(client, fake_env):
    fake_env.setenv("FAKE_DELAY", "3")
    collection = queue(client).json()["collection"]

    blocked = client.delete(f"/api/collections/{collection['id']}")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "INVALID_STATE"

    canceled = client.post(f"/api/collections/{collection['id']}/cancel")
    assert canceled.status_code == 200, canceled.text
    body = canceled.json()
    assert body["active_total"] == 0, body["counts"]
    assert body["failed_total"] == 3, body["counts"]
    assert body["counts"] == {"canceled": 3}

    fake_env.setenv("FAKE_DELAY", "0")
    retried = client.post(f"/api/collections/{collection['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["failed_total"] == 0
    settled = wait_until_settled(client, collection["id"])
    assert settled["completed_total"] == 3


def test_delete_collection_with_its_files(client):
    collection = queue(client, ["vid001"]).json()["collection"]
    wait_until_settled(client, collection["id"])
    (item,) = items_of(client, collection["id"])
    output = Path(item["output_path"])
    assert output.is_file()

    response = client.delete(
        f"/api/collections/{collection['id']}", params={"delete_files": True}
    )
    assert response.status_code == 204
    assert not output.exists()
    assert client.get(f"/api/collections/{collection['id']}").status_code == 404
    assert client.get(f"/api/downloads/{item['id']}").status_code == 404


def test_removing_the_last_item_removes_the_collection(client):
    collection = queue(client, ["vid001", "vid002"]).json()["collection"]
    wait_until_settled(client, collection["id"])
    first, second = items_of(client, collection["id"])

    assert client.delete(f"/api/downloads/{first['id']}").status_code == 204
    remaining = client.get(f"/api/collections/{collection['id']}").json()
    assert remaining["item_total"] == 1

    assert client.delete(f"/api/downloads/{second['id']}").status_code == 204
    assert client.get(f"/api/collections/{collection['id']}").status_code == 404


def test_collections_are_listed_newest_first(client):
    older = queue(client, ["vid001"]).json()["collection"]
    newer = queue(client, ["vid002"], mode="audio").json()["collection"]
    listing = client.get("/api/collections").json()
    assert listing["total"] == 2
    assert [c["id"] for c in listing["items"]] == [newer["id"], older["id"]]
    assert client.get("/api/collections/unknown").status_code == 404


def test_collection_events_reach_websocket_clients(client):
    with client.websocket_connect("/api/ws") as ws:
        ws.send_json({"type": "auth", "token": client.app.state.token})
        assert ws.receive_json()["type"] == "snapshot"
        collection = queue(client, ["vid001"]).json()["collection"]

        seen = []
        while not {"collection.created", "collection.updated"} <= set(seen):
            message = ws.receive_json()
            seen.append(message["type"])
            if message["type"].startswith("collection."):
                assert message["collection"]["id"] == collection["id"]
