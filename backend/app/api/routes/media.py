import re

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

from app.core.errors import AppError

router = APIRouter(prefix="/api/media", tags=["media"])
THUMB_RE = re.compile(r"^[a-f0-9]{40}\.jpg$")


@router.get("/thumbnails/{name}")
async def thumbnail(name: str, request: Request) -> Response:
    if not THUMB_RE.match(name):
        raise AppError("NOT_FOUND", "Thumbnail not found", 404)
    path = request.app.state.config.thumbnails_dir / name
    if not path.is_file():
        raise AppError("NOT_FOUND", "Thumbnail not found", 404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})
