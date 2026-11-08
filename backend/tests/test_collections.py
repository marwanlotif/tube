import json

import pytest

from app.domain.collections import is_collection, parse_collection
from tests.conftest import FAKES


def _load(name: str) -> dict:
    return json.loads((FAKES / name).read_text())


@pytest.fixture
def playlist() -> dict:
    return _load("playlist.json")


def test_is_collection_distinguishes_listings_from_videos(playlist):
    assert is_collection(playlist)
    assert is_collection({"_type": "multi_video", "entries": []})
    assert is_collection({"entries": [], "id": "x"})
    assert not is_collection(_load("info.json"))


def test_playlist_entries_keep_source_positions_and_drop_duplicates(playlist):
    listing = parse_collection(playlist, limit=500)

    assert listing.kind == "playlist"
    assert listing.title == "Test Playlist"
    assert listing.uploader == "Tester"
    assert listing.total == 8
    assert listing.truncated is False
    ids = [e.id for e in listing.entries]
    assert ids == ["vid001", "vid002", "vidpriv", "vidsoon", "local", "vid003"]
    # Indexes are positions in the source, so a skipped None/duplicate leaves a gap.
    assert [e.index for e in listing.entries] == [1, 2, 4, 6, 7, 8]


def test_entry_fields_are_normalised(playlist):
    listing = parse_collection(playlist, limit=500)
    second = listing.entry("vid002")
    assert second.duration_s == 125
    assert second.url == "https://www.youtube.com/watch?v=vid002"
    assert second.available and second.reason is None
    assert second.extractor == "Youtube"
    assert listing.entry("vid003").duration_s is None


@pytest.mark.parametrize(
    ("entry_id", "reason"),
    [
        ("vidpriv", "No longer available"),
        ("vidsoon", "Not yet available"),
        ("local", "Unsupported link"),
    ],
)
def test_unavailable_entries_are_flagged_not_dropped(playlist, entry_id, reason):
    entry = parse_collection(playlist, limit=500).entry(entry_id)
    assert entry.available is False
    assert entry.reason == reason


def test_availability_field_marks_restricted_entries():
    payload = {
        "_type": "playlist",
        "id": "PL1",
        "entries": [
            {"id": "a", "url": "https://x.test/a", "availability": "subscriber_only"},
            {"id": "b", "url": "https://x.test/b", "availability": "public"},
            {"id": "c", "url": "https://x.test/c", "live_status": "is_live"},
        ],
    }
    listing = parse_collection(payload, limit=10)
    assert [(e.id, e.available, e.reason) for e in listing.entries] == [
        ("a", False, "Members only"),
        ("b", True, None),
        ("c", False, "Live now"),
    ]


def test_channel_tabs_and_linked_playlists_are_nested_collections():
    listing = parse_collection(_load("channel.json"), limit=500)

    assert listing.kind == "channel"
    # Both tabs share the channel id; they must not be collapsed as duplicates.
    assert [(e.kind, e.title) for e in listing.entries] == [
        ("collection", "Tester - Videos"),
        ("collection", "Tester - Shorts"),
        ("collection", "Test Playlist"),
    ]
    tab, _, linked = listing.entries
    assert tab.url == tab.id == "https://www.youtube.com/@tester/videos"
    assert linked.url == "https://www.youtube.com/playlist?list=PLtest123"
    # Nested listings are never offered as downloadable videos.
    assert listing.videos == []
    assert listing.entry("PLtest123") is None


def test_channel_tab_is_detected_by_channel_id():
    payload = {"_type": "playlist", "id": "UC1", "channel_id": "UC1", "entries": []}
    assert parse_collection(payload, limit=10).kind == "channel"


def test_same_extractor_url_with_duration_is_still_a_video():
    payload = {
        "_type": "playlist",
        "id": "set",
        "extractor_key": "Site",
        "entries": [{"_type": "url", "ie_key": "Site", "id": "t1",
                     "url": "https://x.test/t1", "duration": 30}],
    }
    assert parse_collection(payload, limit=10).entries[0].kind == "video"


@pytest.mark.parametrize(
    ("count", "reported", "truncated"),
    [
        (3, 10, True),  # hit the cap and the site reports more
        (3, None, True),  # hit the cap and the size is unknown
        (3, 3, False),  # exactly the cap and nothing more
        (2, None, False),  # below the cap
    ],
)
def test_truncation_reflects_the_requested_limit(count, reported, truncated):
    payload = {
        "_type": "playlist",
        "id": "PL1",
        "playlist_count": reported,
        "entries": [{"id": str(i), "url": f"https://x.test/{i}"} for i in range(count)],
    }
    assert parse_collection(payload, limit=3).truncated is truncated


def test_entries_without_any_identifier_are_skipped():
    payload = {"_type": "playlist", "id": "PL1", "entries": [{"title": "orphan"}, "junk"]}
    assert parse_collection(payload, limit=10).entries == []
