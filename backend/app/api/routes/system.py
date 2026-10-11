from fastapi import APIRouter, Request

from app.schemas.video import StatsOut, SystemOut
from app.services.settings import load_settings
from app.services.storage import disk_info

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/system", response_model=SystemOut)
async def system(request: Request) -> dict:
    state = request.app.state
    settings = await load_settings(state.settings_repo, state.config)
    return {
        "ytdlp_version": state.binaries.ytdlp_version,
        "ffmpeg_version": state.binaries.ffmpeg_version,
        "ytdlp_ok": bool(state.binaries.ytdlp and state.binaries.ytdlp_version),
        "ffmpeg_ok": bool(state.binaries.ffmpeg and state.binaries.ffmpeg_version),
        "data_dir": str(state.config.data_dir),
        "video_dir": settings.video_dir,
        "audio_dir": settings.audio_dir,
        "allowed_roots": [str(r) for r in state.config.media_roots],
        "max_concurrent_downloads": settings.max_concurrent_downloads,
        "log_dir": str(state.config.logs_dir),
    }


@router.get("/stats", response_model=StatsOut)
async def stats(request: Request) -> dict:
    state = request.app.state
    data = await state.repo.stats()
    free, total = await disk_info(state.config.data_dir)
    return {**data, "disk_free": free, "disk_total": total}
