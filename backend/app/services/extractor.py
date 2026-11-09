import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from app.core.errors import AppError, redact
from app.domain.formats import FormatOption, ResolvedSelection, parse_formats, preset_list
from app.integrations.ytdlp import info_argv
from app.services.storage import fetch_thumbnail

log = logging.getLogger(__name__)

CACHE_TTL = 600.0


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


class Extractor:
    def __init__(self, binary: str, thumbnails_dir, timeout: float = 60.0):
        self.binary = binary
        self.thumbnails_dir = thumbnails_dir
        self.timeout = timeout
        # Keyed by (url, cookie source): a signed-in extraction can expose different formats.
        self._cache: dict[tuple[str, str | None], tuple[float, VideoInfo]] = {}
        self._locks: dict[tuple[str, str | None], asyncio.Lock] = {}

    def cached(self, url: str, cookies_from_browser: str | None = None) -> VideoInfo | None:
        hit = self._cache.get((url, cookies_from_browser))
        if hit and time.monotonic() - hit[0] < CACHE_TTL:
            return hit[1]
        return None

    async def extract(
        self, url: str, force: bool = False, cookies_from_browser: str | None = None
    ) -> VideoInfo:
        key = (url, cookies_from_browser)
        if not force:
            hit = self.cached(*key)
            if hit:
                return hit
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if not force:
                hit = self.cached(*key)
                if hit:
                    return hit
            info = await self._extract(url, cookies_from_browser)
            self._cache[key] = (time.monotonic(), info)
            return info

    async def _extract(self, url: str, cookies_from_browser: str | None) -> VideoInfo:
        try:
            proc = await asyncio.create_subprocess_exec(
                *info_argv(self.binary, url, cookies_from_browser),
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
        if payload.get("_type") in {"playlist", "multi_video"} or (
            "entries" in payload and not payload.get("formats")
        ):
            raise AppError("PLAYLIST_UNSUPPORTED", "Playlists are not supported yet", 422)

        raw_formats = payload.get("formats") or []
        options = parse_formats(raw_formats)
        if not options:
            raise AppError("NO_FORMATS", "No downloadable formats were found", 422)

        thumbnail_name = None
        thumbnails = [
            t
            for t in payload.get("thumbnails") or []
            if t.get("url") and t.get("width")
        ]
        thumbnails.sort(key=lambda t: t.get("width") or 0, reverse=True)
        for thumb in thumbnails[:3]:
            if (thumb.get("width") or 0) > 1920:
                continue
            thumbnail_name = await fetch_thumbnail(thumb["url"], self.thumbnails_dir)
            if thumbnail_name:
                break

        video = VideoInfo(
            id=str(payload.get("id") or ""),
            title=str(payload.get("title") or "Untitled"),
            webpage_url=str(payload.get("webpage_url") or url),
            site=payload.get("extractor_key") or payload.get("extractor"),
            uploader=payload.get("uploader") or payload.get("channel"),
            duration_s=int(payload["duration"]) if payload.get("duration") else None,
            thumbnail_name=thumbnail_name,
            is_live=bool(payload.get("is_live")),
            formats=options,
            presets=preset_list(options),
            extracted_at=time.time(),
        )
        return video

    @staticmethod
    def resolve(video: VideoInfo, preset: str | None, video_id: str | None,
                audio_id: str | None) -> ResolvedSelection | None:
        from app.domain.formats import resolve_custom, resolve_preset

        if video_id:
            return resolve_custom(video.formats, video_id, audio_id)
        return resolve_preset(video.formats, preset or "best_1080")
