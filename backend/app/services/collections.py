"""Queue a playlist or channel as one collection of ordinary download jobs."""

import asyncio
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.core.config import Config
from app.core.errors import AppError
from app.db.repos import CollectionRepo, DownloadRepo
from app.db.tables import CollectionRow, DownloadRow
from app.domain import urls
from app.domain.collections import CollectionEntry, CollectionListing
from app.domain.enums import Status
from app.domain.formats import PRESET_KEYS, PRESET_LABELS
from app.domain.naming import render_playlist_index, safe_folder_name, validate_template
from app.schemas.settings import SettingsModel
from app.schemas.video import CollectionCreate
from app.services.extractor import Extractor
from app.services.job_spec import job_options, needs_ffmpeg
from app.services.storage import validate_output_dir


@dataclass
class QueueResult:
    collection: CollectionRow
    items: list[DownloadRow]
    skipped: Counter


def select_entries(
    listing: CollectionListing, entry_ids: list[str]
) -> tuple[list[CollectionEntry], Counter]:
    """Map requested ids onto downloadable entries, in playlist order."""
    skipped: Counter = Counter()
    chosen: dict[str, CollectionEntry] = {}
    for entry_id in dict.fromkeys(entry_ids):  # de-duplicate, keep request order
        entry = listing.entry(entry_id)
        if entry is None:
            skipped["not_found"] += 1
        elif not entry.available:
            skipped["unavailable"] += 1
        else:
            chosen[entry.id] = entry
    return sorted(chosen.values(), key=lambda e: e.index), skipped


async def _public_entries(
    entries: list[CollectionEntry],
) -> tuple[list[tuple[CollectionEntry, str]], int]:
    """Normalise every entry URL and check each distinct host against private ranges once."""
    verdicts: dict[str, bool] = {}
    allowed: list[tuple[CollectionEntry, str]] = []
    blocked = 0
    for entry in entries:
        try:
            url = urls.normalize_url(entry.url or "")
        except AppError:
            blocked += 1
            continue
        host = urlsplit(url).hostname or ""
        if host not in verdicts:
            try:
                await asyncio.to_thread(urls.assert_public_host, host)
                verdicts[host] = True
            except AppError:
                verdicts[host] = False
        if verdicts[host]:
            allowed.append((entry, url))
        else:
            blocked += 1
    return allowed, blocked


async def _drop_existing(
    entries: list[tuple[CollectionEntry, str]], mode: str, downloads: DownloadRepo
) -> tuple[list[tuple[CollectionEntry, str]], int]:
    existing = await downloads.existing_videos(mode, [entry.id for entry, _ in entries])
    known_ids = {video_id for _, video_id in existing}
    kept = [
        (entry, url)
        for entry, url in entries
        if not (
            (entry.extractor, entry.id) in existing
            or (entry.extractor is None and entry.id in known_ids)
        )
    ]
    return kept, len(entries) - len(kept)


def _output_dir(base: str, listing: CollectionListing, subfolder: bool, config: Config) -> str:
    if not subfolder:
        return base
    folder = Path(base) / safe_folder_name(listing.title, listing.id)
    return str(validate_output_dir(str(folder), config.media_roots))


async def queue_collection(
    payload: CollectionCreate,
    *,
    url: str,
    settings: SettingsModel,
    config: Config,
    extractor: Extractor,
    downloads: DownloadRepo,
    collections: CollectionRepo,
    ffmpeg_available: bool,
) -> QueueResult:
    """Create a collection row plus one queued download per selected video.

    Items keep the listing's metadata until their own job runs, extracts the video and
    resolves the preset (see ``DownloadManager``), exactly like a retried download.
    """
    mode = payload.mode
    preset = "audio" if mode == "audio" else (payload.preset or "best_1080")
    if preset not in PRESET_KEYS:
        raise AppError("INVALID_PRESET", f"Unknown preset: {preset}", 422)
    options = job_options(
        settings,
        mode=mode,
        audio_format=payload.audio_format,
        subtitles=payload.subtitles,
        subtitle_langs=payload.subtitle_langs,
    )
    if needs_ffmpeg(options, requires_merge=False) and not ffmpeg_available:
        raise AppError("FFMPEG_MISSING", "ffmpeg is not installed or not on PATH", 503)

    info = await extractor.extract_collection(
        url, cookies_from_browser=settings.cookies_from_browser
    )
    listing = info.listing
    chosen, skipped = select_entries(listing, payload.entry_ids)
    allowed, skipped["blocked"] = await _public_entries(chosen)
    if payload.skip_existing:
        allowed, skipped["already_downloaded"] = await _drop_existing(allowed, mode, downloads)
    if not allowed:
        raise AppError(
            "NOTHING_TO_DOWNLOAD",
            "None of the selected videos can be added",
            422,
            {"skipped": dict(skipped)},
        )

    output_dir = _output_dir(options["output_dir"], listing, payload.subfolder, config)
    count = max(listing.total or 0, max(e.index for e in listing.entries))
    container = options["audio_format"] if mode == "audio" else None
    items = []
    for entry, entry_url in allowed:
        template = validate_template(
            render_playlist_index(options["filename_template"], entry.index, count)
        )
        items.append(
            {
                "id": str(uuid.uuid4()),
                "url": entry_url,
                "site": entry.extractor,
                "video_id": entry.id,
                "title": entry.title,
                "duration_s": entry.duration_s,
                "mode": mode,
                "status": Status.QUEUED.value,
                "format_label": PRESET_LABELS[preset],
                "container": container,
                "output_dir": output_dir,
                "playlist_index": entry.index,
                "resumable": False,
                "job_spec": {
                    **options,
                    "url": entry_url,
                    "output_dir": output_dir,
                    "filename_template": template,
                    "preset_key": preset,
                    "selector": None,
                    "revalidate": True,  # formats are resolved when the item runs
                },
            }
        )

    collection, rows = await collections.create_with_items(
        {
            "id": str(uuid.uuid4()),
            "url": url,
            "source_id": listing.id or None,
            "collection_type": listing.kind,
            "title": listing.title,
            "uploader": listing.uploader,
            "site": listing.site,
            "thumbnail_name": info.thumbnail_name,
            "mode": mode,
            "preset_key": preset,
            "output_dir": output_dir,
            "entry_total": len(items),
        },
        items,
    )
    return QueueResult(collection=collection, items=rows, skipped=skipped)
