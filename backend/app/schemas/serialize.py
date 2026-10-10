from datetime import UTC

from app.db.tables import DownloadRow
from app.domain.formats import FormatOption
from app.schemas.video import DownloadOut, FormatOut, PresetOut, VideoInfoOut
from app.services.extractor import VideoInfo


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
        thumbnail_url=(
            f"/api/media/thumbnails/{row.thumbnail_name}" if row.thumbnail_name else None
        ),
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
        thumbnail_url=(
            f"/api/media/thumbnails/{video.thumbnail_name}" if video.thumbnail_name else None
        ),
        is_live=video.is_live,
        formats=[format_out(f) for f in video.formats],
        presets=[PresetOut(**p) for p in video.presets],
    ).model_dump()
