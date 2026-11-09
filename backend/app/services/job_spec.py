"""Job spec fields shared by single downloads and playlist items."""

from typing import Any

from app.core.errors import AppError
from app.schemas.settings import SettingsModel
from app.services.settings import LANGS_RE


def job_options(
    settings: SettingsModel,
    *,
    mode: str,
    audio_format: str | None = None,
    subtitles: bool | None = None,
    subtitle_langs: str | None = None,
) -> dict[str, Any]:
    """Resolve settings plus per-request overrides into the spec keys every job carries."""
    subs = settings.subtitles.model_dump()
    if subtitles is not None:
        subs["enabled"] = subtitles
    if subtitle_langs:
        subs["langs"] = subtitle_langs.strip()
    if subs["enabled"] and not LANGS_RE.match(subs["langs"]):
        raise AppError("INVALID_SETTINGS", "Invalid subtitle language list", 422)
    return {
        "mode": mode,
        "output_dir": settings.audio_dir if mode == "audio" else settings.video_dir,
        "filename_template": settings.filename_template,
        "audio_format": audio_format or settings.audio.format,
        "audio_quality": settings.audio.quality,
        "subtitles": subs,
        "network": settings.network.model_dump(),
        "cookies_from_browser": settings.cookies_from_browser,
    }


def needs_ffmpeg(options: dict[str, Any], requires_merge: bool) -> bool:
    return options["mode"] == "audio" or requires_merge or bool(options["subtitles"].get("embed"))
