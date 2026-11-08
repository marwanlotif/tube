import asyncio

from fastapi import APIRouter, Request

from app.domain.urls import validate_url
from app.schemas.serialize import collection_info_out, video_out
from app.schemas.video import ProbeOut, VideoInfoRequest
from app.services.extractor import CollectionInfo
from app.services.settings import load_settings

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/info", response_model=ProbeOut)
async def video_info(payload: VideoInfoRequest, request: Request) -> dict:
    """Describe a link: a single video with its formats, or a playlist/channel listing."""
    state = request.app.state
    url = await asyncio.to_thread(validate_url, payload.url)
    settings = await load_settings(state.settings_repo, state.config)
    result = await state.extractor.probe(
        url, cookies_from_browser=settings.cookies_from_browser, playlist=payload.playlist
    )
    if isinstance(result, CollectionInfo):
        return collection_info_out(result, state.config.max_collection_entries)
    return video_out(result)
