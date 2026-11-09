import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.core.errors import AppError
from app.domain.enums import Status
from app.domain.urls import validate_url
from app.schemas.serialize import collection_out, download_out
from app.schemas.video import DownloadCreate, DownloadList, DownloadOut
from app.services.job_spec import job_options, needs_ffmpeg
from app.services.settings import load_settings
from app.services.storage import reveal_file, safe_delete_file

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


async def _collection_item_removed(state, collection_id: str) -> None:
    """Drop a collection once its last item is gone, otherwise refresh its summary."""
    if await state.collections.delete_if_empty(collection_id):
        await state.events.broadcast({"type": "collection.deleted", "id": collection_id})
        return
    summary = await state.collections.summary(collection_id)
    if summary:
        await state.events.broadcast(
            {"type": "collection.updated", "collection": collection_out(summary)}
        )


@router.post("", response_model=DownloadOut, status_code=202)
async def create_download(payload: DownloadCreate, request: Request) -> dict:
    state = request.app.state
    state.binaries.require_ytdlp()
    url = await asyncio.to_thread(validate_url, payload.url)
    settings = await load_settings(state.settings_repo, state.config)
    info = await state.extractor.extract(
        url, cookies_from_browser=settings.cookies_from_browser
    )

    mode = payload.mode
    preset = "audio" if mode == "audio" else (payload.preset or "best_1080")
    resolved = state.extractor.resolve(
        info,
        None if payload.video_id else preset,
        payload.video_id,
        payload.audio_id,
    )
    if resolved is None:
        raise AppError(
            "PRESET_UNAVAILABLE",
            "That quality is not available for this video",
            422,
            {"preset": preset},
        )

    options = job_options(
        settings,
        mode=mode,
        audio_format=payload.audio_format,
        subtitles=payload.subtitles,
        subtitle_langs=payload.subtitle_langs,
    )
    if needs_ffmpeg(options, resolved.requires_merge):
        state.binaries.require_ffmpeg()

    output_dir = options["output_dir"]
    spec = {
        **options,
        "url": url,
        "selector": resolved.selector,
        "container": resolved.container,
        "requires_merge": resolved.requires_merge,
        "preset_key": None if payload.video_id else preset,
        "video_id": payload.video_id,
        "audio_id": payload.audio_id,
        "resolved": {"video_id": resolved.video_id, "audio_id": resolved.audio_id},
        "extracted_at": datetime.now(UTC).isoformat(),
        "revalidate": False,
    }

    row = await state.repo.create(
        id=str(uuid.uuid4()),
        url=url,
        site=info.site,
        video_id=info.id,
        title=info.title,
        uploader=info.uploader,
        thumbnail_name=info.thumbnail_name,
        duration_s=info.duration_s,
        mode=mode,
        status=Status.QUEUED.value,
        format_label=resolved.label,
        format_selector=resolved.selector,
        container=options["audio_format"] if mode == "audio" else resolved.container,
        output_dir=output_dir,
        job_spec=spec,
        resumable=False,
    )
    await state.manager.enqueue(row.id)
    return download_out(row)


@router.get("", response_model=DownloadList)
async def list_downloads(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    collection_id: str | None = Query(default=None),
    standalone: bool = Query(
        default=False, description="Only downloads that are not part of a collection"
    ),
) -> dict:
    state = request.app.state
    parsed: Status | None = None
    if status:
        try:
            parsed = Status(status)
        except ValueError as exc:
            raise AppError("INVALID_STATUS", f"Unknown status: {status}", 422) from exc
    filters = {"collection_id": collection_id, "standalone": standalone}
    rows = await state.repo.list_rows(status=parsed, limit=limit, offset=offset, **filters)
    return {
        "items": [download_out(row) for row in rows],
        "total": await state.repo.count(parsed, **filters),
    }


@router.get("/{download_id}", response_model=DownloadOut)
async def get_download(download_id: str, request: Request) -> dict:
    row = await request.app.state.repo.get(download_id)
    if row is None:
        raise AppError("NOT_FOUND", "Download not found", 404)
    return download_out(row)


@router.post("/{download_id}/cancel", response_model=DownloadOut)
async def cancel_download(download_id: str, request: Request) -> dict:
    state = request.app.state
    await state.manager.cancel(download_id)
    row = await state.repo.get(download_id)
    if row is None:
        raise AppError("NOT_FOUND", "Download not found", 404)
    return download_out(row)


@router.post("/{download_id}/retry", response_model=DownloadOut)
async def retry_download(download_id: str, request: Request) -> dict:
    state = request.app.state
    await state.manager.retry(download_id)
    row = await state.repo.get(download_id)
    if row is None:
        raise AppError("NOT_FOUND", "Download not found", 404)
    return download_out(row)


@router.delete("/{download_id}", status_code=204)
async def delete_download(
    download_id: str,
    request: Request,
    delete_file: bool = Query(default=False),
) -> Response:
    state = request.app.state
    row = await state.repo.get(download_id)
    if row is None:
        raise AppError("NOT_FOUND", "Download not found", 404)
    if row.status in {s.value for s in Status} and row.status not in {
        Status.COMPLETED.value,
        Status.FAILED.value,
        Status.CANCELED.value,
        Status.INTERRUPTED.value,
    }:
        raise AppError("INVALID_STATE", "Cancel the download before deleting it", 409)
    if delete_file and row.output_path:
        safe_delete_file(row.output_path, state.config.media_roots)
    await state.repo.delete(download_id)
    await state.events.broadcast({"type": "download.deleted", "id": download_id})
    if row.collection_id:
        await _collection_item_removed(state, row.collection_id)
    await state.events.broadcast({"type": "stats.updated"})
    return Response(status_code=204)


@router.post("/{download_id}/reveal", status_code=204)
async def reveal_download(download_id: str, request: Request) -> Response:
    state = request.app.state
    row = await state.repo.get(download_id)
    if row is None:
        raise AppError("NOT_FOUND", "Download not found", 404)
    if row.status != Status.COMPLETED.value or not row.output_path:
        raise AppError("INVALID_STATE", "Only completed downloads can be revealed", 409)
    await reveal_file(row.output_path, state.config.media_roots)
    return Response(status_code=204)
