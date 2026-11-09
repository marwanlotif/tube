import asyncio
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.core.errors import AppError
from app.domain.enums import ACTIVE_STATUSES, Status
from app.domain.urls import validate_url
from app.schemas.serialize import collection_out
from app.schemas.video import (
    CollectionCreate,
    CollectionCreated,
    CollectionList,
    CollectionOut,
)
from app.services.collections import queue_collection
from app.services.settings import load_settings
from app.services.storage import safe_delete_file

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/collections", tags=["collections"])


async def _summary_or_404(state, collection_id: str):
    summary = await state.collections.summary(collection_id)
    if summary is None:
        raise AppError("NOT_FOUND", "Collection not found", 404)
    return summary


@router.post("", response_model=CollectionCreated, status_code=202)
async def create_collection(payload: CollectionCreate, request: Request) -> dict:
    state = request.app.state
    state.binaries.require_ytdlp()
    url = await asyncio.to_thread(validate_url, payload.url)
    settings = await load_settings(state.settings_repo, state.config)
    result = await queue_collection(
        payload,
        url=url,
        settings=settings,
        config=state.config,
        extractor=state.extractor,
        downloads=state.repo,
        collections=state.collections,
        ffmpeg_available=bool(state.binaries.ffmpeg),
    )
    for item in result.items:
        await state.manager.enqueue(item.id)

    collection = collection_out(await _summary_or_404(state, result.collection.id))
    await state.events.broadcast({"type": "collection.created", "collection": collection})
    await state.events.broadcast({"type": "stats.updated"})
    return {
        "collection": collection,
        "created": len(result.items),
        "skipped": dict(result.skipped),
    }


@router.get("", response_model=CollectionList)
async def list_collections(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    state = request.app.state
    summaries = await state.collections.summaries(limit=limit, offset=offset)
    return {
        "items": [collection_out(s) for s in summaries],
        "total": await state.collections.count(),
    }


@router.get("/{collection_id}", response_model=CollectionOut)
async def get_collection(collection_id: str, request: Request) -> dict:
    return collection_out(await _summary_or_404(request.app.state, collection_id))


@router.post("/{collection_id}/cancel", response_model=CollectionOut)
async def cancel_collection(collection_id: str, request: Request) -> dict:
    state = request.app.state
    await _summary_or_404(state, collection_id)
    await state.manager.cancel_collection(collection_id)
    await state.events.broadcast({"type": "stats.updated"})
    return collection_out(await _summary_or_404(state, collection_id))


@router.post("/{collection_id}/retry", response_model=CollectionOut)
async def retry_collection(collection_id: str, request: Request) -> dict:
    state = request.app.state
    await _summary_or_404(state, collection_id)
    await state.manager.retry_collection(collection_id)
    await state.events.broadcast({"type": "stats.updated"})
    return collection_out(await _summary_or_404(state, collection_id))


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: str,
    request: Request,
    delete_files: bool = Query(default=False),
) -> Response:
    state = request.app.state
    summary = await _summary_or_404(state, collection_id)
    if summary.count(*ACTIVE_STATUSES):
        raise AppError("INVALID_STATE", "Cancel the remaining downloads before deleting", 409)
    if delete_files:
        rows = await state.repo.list_rows(
            status=Status.COMPLETED, collection_id=collection_id, limit=100_000
        )
        for row in rows:
            if not row.output_path:
                continue
            try:
                safe_delete_file(row.output_path, state.config.media_roots)
            except (AppError, OSError) as exc:
                # Best effort: one unremovable file must not keep the rest on disk.
                log.warning("could not delete %s: %s", row.output_path, exc)
    await state.collections.delete(collection_id)
    await state.events.broadcast({"type": "collection.deleted", "id": collection_id})
    await state.events.broadcast({"type": "stats.updated"})
    return Response(status_code=204)
