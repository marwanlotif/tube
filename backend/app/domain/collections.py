"""Pure parsing of yt-dlp ``--flat-playlist`` output into playlists and channels.

A flat listing only carries lightweight metadata per entry (id, title, URL, sometimes a
duration). Formats are resolved per video later, when each item's job runs.
"""

from dataclasses import dataclass, field
from urllib.parse import urlsplit

COLLECTION_TYPES = {"playlist", "multi_video"}

# yt-dlp ``availability`` values that mean the entry cannot be downloaded anonymously.
UNAVAILABLE = {
    "private": "Private video",
    "premium_only": "Premium only",
    "subscriber_only": "Members only",
    "needs_auth": "Sign-in required",
}
# Placeholder titles YouTube uses for entries it still lists but no longer serves.
PLACEHOLDER_TITLES = {"[private video]", "[deleted video]", "[unavailable video]"}
LIVE_STATUSES = {"is_live": "Live now", "is_upcoming": "Not yet available"}


@dataclass(frozen=True)
class CollectionEntry:
    id: str
    index: int  # 1-based position in the source listing
    title: str
    url: str | None
    duration_s: int | None
    kind: str  # "video" or "collection" (a nested playlist, e.g. a channel tab)
    available: bool
    reason: str | None = None


@dataclass(frozen=True)
class CollectionListing:
    id: str
    kind: str  # "playlist" or "channel"
    title: str
    uploader: str | None
    site: str | None
    webpage_url: str
    total: int | None  # count reported by the site; may exceed len(entries)
    truncated: bool
    entries: list[CollectionEntry] = field(default_factory=list)
    thumbnails: list[dict] = field(default_factory=list)

    @property
    def videos(self) -> list[CollectionEntry]:
        return [e for e in self.entries if e.kind == "video"]

    def entry(self, entry_id: str) -> CollectionEntry | None:
        return next((e for e in self.videos if e.id == entry_id), None)


def is_collection(payload: dict) -> bool:
    if payload.get("_type") in COLLECTION_TYPES:
        return True
    return "entries" in payload and not payload.get("formats")


def _http_url(value) -> str | None:
    if not isinstance(value, str):
        return None
    return value if urlsplit(value).scheme in {"http", "https"} else None


def _duration(value) -> int | None:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


def _entry_kind(raw: dict, parent_extractor: str | None) -> str:
    if raw.get("_type") in COLLECTION_TYPES:
        return "collection"
    # A URL reference handled by the parent's own extractor (and with no duration) is
    # another listing, e.g. a playlist linked from a channel's "Playlists" tab.
    if (
        raw.get("_type") == "url"
        and parent_extractor
        and raw.get("ie_key") == parent_extractor
        and raw.get("duration") is None
    ):
        return "collection"
    return "video"


def _entry_url(raw: dict, kind: str) -> str | None:
    # Nested listings carry their canonical page in webpage_url; videos usually in url.
    keys = ("webpage_url", "url") if kind == "collection" else ("url", "webpage_url")
    for key in keys:
        url = _http_url(raw.get(key))
        if url:
            return url
    return None


def _unavailable_reason(raw: dict, url: str | None) -> str | None:
    if url is None:
        return "Unsupported link"
    title = str(raw.get("title") or "").strip().lower()
    if title in PLACEHOLDER_TITLES:
        return "No longer available"
    availability = raw.get("availability")
    if availability in UNAVAILABLE:
        return UNAVAILABLE[availability]
    live_status = raw.get("live_status")
    if live_status in LIVE_STATUSES:
        return LIVE_STATUSES[live_status]
    return None


def _listing_kind(payload: dict) -> str:
    listing_id = payload.get("id")
    if listing_id and listing_id in {payload.get("channel_id"), payload.get("uploader_id")}:
        return "channel"
    return "playlist"


def parse_collection(payload: dict, limit: int) -> CollectionListing:
    """Normalise a flat listing. ``limit`` is the entry cap the listing was requested with."""
    parent_extractor = payload.get("extractor_key")
    raw_entries = payload.get("entries") or []
    entries: list[CollectionEntry] = []
    seen: set[tuple[str, str]] = set()

    for index, raw in enumerate(raw_entries, start=1):
        if not isinstance(raw, dict):
            continue  # yt-dlp yields None for entries it could not resolve
        kind = _entry_kind(raw, parent_extractor)
        url = _entry_url(raw, kind)
        # Nested listings are keyed by URL: a channel's tabs all share the channel's id.
        entry_id = str((url if kind == "collection" else None) or raw.get("id") or url or "")
        if not entry_id or (kind, entry_id) in seen:
            continue
        seen.add((kind, entry_id))
        reason = _unavailable_reason(raw, url)
        entries.append(
            CollectionEntry(
                id=entry_id,
                index=index,
                title=str(raw.get("title") or entry_id),
                url=url,
                duration_s=_duration(raw.get("duration")),
                kind=kind,
                available=reason is None,
                reason=reason,
            )
        )

    reported = payload.get("playlist_count")
    total = reported if isinstance(reported, int) and reported >= 0 else None
    truncated = len(raw_entries) >= limit and (total is None or total > limit)
    return CollectionListing(
        id=str(payload.get("id") or ""),
        kind=_listing_kind(payload),
        title=str(payload.get("title") or "Untitled"),
        uploader=payload.get("uploader") or payload.get("channel"),
        site=payload.get("extractor_key") or payload.get("extractor"),
        webpage_url=_http_url(payload.get("webpage_url")) or "",
        total=total,
        truncated=truncated,
        entries=entries,
        thumbnails=[t for t in payload.get("thumbnails") or [] if isinstance(t, dict)],
    )
