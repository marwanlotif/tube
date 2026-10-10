import asyncio

from fastapi import APIRouter, Request

from app.domain.urls import validate_url
from app.schemas.serialize import video_out
from app.schemas.video import VideoInfoOut, VideoInfoRequest

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/info", response_model=VideoInfoOut)
async def video_info(payload: VideoInfoRequest, request: Request) -> dict:
    url = await asyncio.to_thread(validate_url, payload.url)
    video = await request.app.state.extractor.extract(url)
    return video_out(video)
