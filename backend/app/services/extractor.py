import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from app.core.errors import AppError, redact
from app.domain.collections import CollectionListing, is_collection, parse_collection
from app.domain.formats import (
    FormatOption,
    ResolvedSelection,
    parse_formats,
    preset_list,
    resolve_custom,
    resolve_preset,
)
from app.domain.urls import looks_like_playlist_member
from app.integrations.ytdlp import info_argv
from app.services.storage import fetch_thumbnail

log = logging.getLogger(__name__)

CACHE_TTL = 600.0
MAX_THUMBNAIL_WIDTH = 1920


@dataclass
class VideoInfo:
    id: str
    title: str
    webpage_url: str
    site: str | None
    uploader: str | None
    duration_s: int | None
    thumbnail_name: str | None
    is_live: bool
    formats: list[FormatOption] = field(default_factory=list)
    presets: list[dict] = field(default_factory=list)
    extracted_at: float = 0.0
    playlist_hint: bool = False  # the link also points at a playlist


@dataclass
class CollectionInfo:
    listing: CollectionListing
    thumbnail_name: str | None
    extracted_at: float = 0.0


Probed = VideoInfo | CollectionInfo
# (url, cookie source, playlist requested). A signed-in extraction can expose different
# formats, and the same link can mean a video or its playlist depending on the flag.
CacheKey = tuple[str, str | None, bool]


class Extractor:
    def __init__(
        self,
        binary: str,
        thumbnails_dir,
        timeout: float = 120.0,
        max_entries: int = 500,
    ):
        self.binary = binary
        self.thumbnails_dir = thumbnails_dir
        # Generous enough for a flat listing of ``max_entries`` items, which pages through
        # the site, not only for a single video.
        self.timeout = timeout
        self.max_entries = max_entries
        self._cache: dict[CacheKey, tuple[float, Probed]] = {}
        self._locks: dict[CacheKey, asyncio.Lock] = {}

    def _fresh(self, key: CacheKey) -> Probed | None:
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1]
        return None

    async def probe(
        self,
        url: str,
        cookies_from_browser: str | None = None,
        playlist: bool = False,
        force: bool = False,
    ) -> Probed:
        """Extract a link that may be a single video or a playlist/channel listing."""
        key = (url, cookies_from_browser, playlist)
        if not force and (hit := self._fresh(key)):
            return hit
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if not force and (hit := self._fresh(key)):
                return hit
            payload = await self._run(url, cookies_from_browser, playlist)
            result = await self._build(payload, url)
            now = time.monotonic()
            self._cache[key] = (now, result)
            if isinstance(result, CollectionInfo):
                # Asking for the playlist explicitly would return this same listing.
                self._cache[(url, cookies_from_browser, True)] = (now, result)
            return result

    async def extract(
        self, url: str, force: bool = False, cookies_from_browser: str | None = None
    ) -> VideoInfo:
        result = await self.probe(url, cookies_from_browser, playlist=False, force=force)
        if isinstance(result, CollectionInfo):
            raise AppError(
                "IS_COLLECTION", "This link is a playlist or channel, not a single video", 422
            )
        return result

    async def extract_collection(
        self, url: str, cookies_from_browser: str | None = None, force: bool = False
    ) -> CollectionInfo:
        result = await self.probe(url, cookies_from_browser, playlist=True, force=force)
        if isinstance(result, VideoInfo):
            raise AppError(
                "NOT_A_COLLECTION", "This link is a single video, not a playlist", 422
            )
        return result

    async def _run(self, url: str, cookies_from_browser: str | None, playlist: bool) -> dict:
        argv = info_argv(self.binary, url, cookies_from_browser, playlist, self.max_entries)
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise AppError("YTDLP_MISSING", f"Cannot start yt-dlp: {exc}", status=503) from exc
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), self.timeout)
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AppError("EXTRACTION_TIMEOUT", "Extraction timed out", status=504) from exc
        if proc.returncode != 0:
            stderr_text = redact(stderr.decode(errors="replace").strip())
            last = stderr_text.splitlines()[-1] if stderr_text else "yt-dlp failed"
            raise AppError(
                "EXTRACTION_FAILED",
                last[:500],
                status=422,
                details={"hint": "The site may need cookies. Try Settings → Cookies."},
            )
        try:
            payload = json.loads(stdout.decode(errors="replace"))
        except json.JSONDecodeError as exc:
            raise AppError("EXTRACTION_FAILED", "yt-dlp returned invalid JSON", 502) from exc
        if not isinstance(payload, dict):
            raise AppError("EXTRACTION_FAILED", "Unexpected extraction result", 502)
        return payload

    async def _build(self, payload: dict, url: str) -> Probed:
        if is_collection(payload):
            listing = parse_collection(payload, self.max_entries)
            if not listing.entries:
                raise AppError("NO_ENTRIES", "This playlist has no entries", 422)
            return CollectionInfo(
                listing=listing,
                thumbnail_name=await self._thumbnail(listing.thumbnails),
                extracted_at=time.time(),
            )

        options = parse_formats(payload.get("formats") or [])
        if not options:
            raise AppError("NO_FORMATS", "No downloadable formats were found", 422)
        return VideoInfo(
            id=str(payload.get("id") or ""),
            title=str(payload.get("title") or "Untitled"),
            webpage_url=str(payload.get("webpage_url") or url),
            site=payload.get("extractor_key") or payload.get("extractor"),
            uploader=payload.get("uploader") or payload.get("channel"),
            duration_s=int(payload["duration"]) if payload.get("duration") else None,
            thumbnail_name=await self._thumbnail(payload.get("thumbnails") or []),
            is_live=bool(payload.get("is_live")),
            formats=options,
            presets=preset_list(options),
            extracted_at=time.time(),
            playlist_hint=looks_like_playlist_member(url),
        )

    async def _thumbnail(self, thumbnails: list[dict]) -> str | None:
        candidates = [
            t for t in thumbnails if isinstance(t, dict) and t.get("url") and t.get("width")
        ]
        candidates.sort(key=lambda t: t.get("width") or 0, reverse=True)
        for thumb in candidates[:3]:
            if (thumb.get("width") or 0) > MAX_THUMBNAIL_WIDTH:
                continue
            name = await fetch_thumbnail(thumb["url"], self.thumbnails_dir)
            if name:
                return name
        return None

    @staticmethod
    def resolve(video: VideoInfo, preset: str | None, video_id: str | None,
                audio_id: str | None) -> ResolvedSelection | None:
        if video_id:
            return resolve_custom(video.formats, video_id, audio_id)
        return resolve_preset(video.formats, preset or "best_1080")
