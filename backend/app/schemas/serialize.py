from datetime import UTC

from app.db.repos import CollectionSummary
from app.db.tables import DownloadRow
from app.domain.enums import ACTIVE_STATUSES, RETRYABLE_STATUSES, Status
from app.domain.formats import FormatOption, preset_choices
from app.schemas.video import (
    CollectionEntryOut,
    CollectionInfoOut,
    CollectionOut,
    DownloadOut,
    FormatOut,
    PresetOut,
    VideoInfoOut,
)
from app.services.extractor import CollectionInfo, VideoInfo


def _thumbnail_url(name: str | None) -> str | None:
    return f"/api/media/thumbnails/{name}" if name else None


def _aware(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def download_out(row: DownloadRow) -> dict:
    return DownloadOut(
        id=row.id,
        url=row.url,
        site=row.site,
        video_id=row.video_id,
        title=row.title,
        uploader=row.uploader,
        thumbnail_url=_thumbnail_url(row.thumbnail_name),
        duration_s=row.duration_s,
        mode=row.mode,
        status=row.status,
        format_label=row.format_label,
        format_selector=row.format_selector,
        container=row.container,
        output_dir=row.output_dir,
        output_path=row.output_path,
        file_size=row.file_size,
        downloaded_bytes=row.downloaded_bytes or 0,
        total_bytes=row.total_bytes,
        progress=row.progress or 0.0,
        speed=row.speed,
        eta_s=row.eta_s,
        error_code=row.error_code,
        error_message=row.error_message,
        attempts=row.attempts or 0,
        resumable=row.resumable,
        created_at=_aware(row.created_at),
        started_at=_aware(row.started_at),
        finished_at=_aware(row.finished_at),
        collection_id=row.collection_id,
        playlist_index=row.playlist_index,
    ).model_dump(mode="json")


def collection_out(summary: CollectionSummary) -> dict:
    row = summary.row
    total = summary.item_total
    completed = summary.count(Status.COMPLETED)
    # Completed items count in full, items in progress by their own progress; failed or
    # canceled items count as not done.
    progress = (100.0 * completed + summary.active_progress) / total if total else 0.0
    return CollectionOut(
        id=row.id,
        url=row.url,
        collection_type=row.collection_type,
        title=row.title,
        uploader=row.uploader,
        site=row.site,
        thumbnail_url=_thumbnail_url(row.thumbnail_name),
        mode=row.mode,
        preset_key=row.preset_key,
        output_dir=row.output_dir,
        entry_total=row.entry_total,
        item_total=total,
        counts=summary.counts,
        active_total=summary.count(*ACTIVE_STATUSES),
        completed_total=completed,
        failed_total=summary.count(*RETRYABLE_STATUSES),
        progress=round(min(100.0, progress), 2),
        created_at=_aware(row.created_at),
    ).model_dump(mode="json")


def format_out(option: FormatOption) -> dict:
    return FormatOut(
        format_id=option.format_id,
        ext=option.ext,
        kind=option.kind,
        vcodec=option.vcodec,
        acodec=option.acodec,
        width=option.width,
        height=option.height,
        fps=option.fps,
        tbr=option.tbr,
        filesize=option.filesize,
        hdr=option.hdr,
        label=option.label,
    ).model_dump()


def video_out(video: VideoInfo) -> dict:
    return VideoInfoOut(
        id=video.id,
        site=video.site,
        title=video.title,
        uploader=video.uploader,
        duration_s=video.duration_s,
        webpage_url=video.webpage_url,
        thumbnail_url=_thumbnail_url(video.thumbnail_name),
        is_live=video.is_live,
        formats=[format_out(f) for f in video.formats],
        presets=[PresetOut(**p) for p in video.presets],
        playlist_hint=video.playlist_hint,
    ).model_dump()


def collection_info_out(info: CollectionInfo, max_entries: int) -> dict:
    listing = info.listing
    return CollectionInfoOut(
        id=listing.id,
        collection_type=listing.kind,
        title=listing.title,
        uploader=listing.uploader,
        site=listing.site,
        webpage_url=listing.webpage_url,
        thumbnail_url=_thumbnail_url(info.thumbnail_name),
        total=listing.total,
        truncated=listing.truncated,
        max_entries=max_entries,
        entries=[
            CollectionEntryOut(
                id=e.id,
                index=e.index,
                title=e.title,
                url=e.url,
                duration_s=e.duration_s,
                kind=e.kind,
                available=e.available,
                reason=e.reason,
            )
            for e in listing.entries
        ],
        presets=[PresetOut(**p) for p in preset_choices()],
    ).model_dump()
