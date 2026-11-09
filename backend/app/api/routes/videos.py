import asyncio

from fastapi import APIRouter, Request

from app.domain.urls import validate_url
from app.schemas.serialize import video_out
from app.schemas.video import VideoInfoOut, VideoInfoRequest
from app.services.settings import load_settings

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/info", response_model=VideoInfoOut)
async def video_info(payload: VideoInfoRequest, request: Request) -> dict:
    state = request.app.state
    url = await asyncio.to_thread(validate_url, payload.url)
    settings = await load_settings(state.settings_repo, state.config)
    video = await state.extractor.extract(
        url, cookies_from_browser=settings.cookies_from_browser
    )
    return video_out(video)
