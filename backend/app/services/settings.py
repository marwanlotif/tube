import re

from app.core.config import Config
from app.core.errors import AppError
from app.db.repos import SettingsRepo
from app.domain.naming import DEFAULT_TEMPLATE, validate_template
from app.schemas.settings import (
    AUDIO_FORMATS,
    COOKIE_SOURCES,
    SettingsModel,
)
from app.services.storage import validate_output_dir

RATE_RE = re.compile(r"^\d+(\.\d+)?[KMG]?$")
LANGS_RE = re.compile(r"^[a-zA-Z0-9.,_-]{1,120}$")


def default_settings(config: Config) -> SettingsModel:
    roots = config.media_roots
    video_root = next((r for r in roots if r.name == "Videos"), roots[0])
    audio_root = next((r for r in roots if r.name == "Music"), roots[0])
    return SettingsModel(
        video_dir=str(video_root / "VidDwn"),
        audio_dir=str(audio_root / "VidDwn"),
        filename_template=DEFAULT_TEMPLATE,
        max_concurrent_downloads=config.max_concurrent_downloads,
    )


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def normalize_settings(data: dict, config: Config) -> SettingsModel:
    merged = _deep_merge(default_settings(config).model_dump(), data or {})
    try:
        settings = SettingsModel.model_validate(merged)
    except Exception as exc:
        raise AppError("INVALID_SETTINGS", str(exc), 422) from exc

    settings.filename_template = validate_template(settings.filename_template)
    settings.video_dir = str(validate_output_dir(settings.video_dir, config.media_roots))
    settings.audio_dir = str(validate_output_dir(settings.audio_dir, config.media_roots))

    if settings.audio.format not in AUDIO_FORMATS:
        raise AppError("INVALID_SETTINGS", "Unsupported audio format", 422)
    if settings.audio.quality not in {str(i) for i in range(10)}:
        raise AppError("INVALID_SETTINGS", "Audio quality must be 0-9", 422)
    if settings.cookies_from_browser in {"", "none"}:
        settings.cookies_from_browser = None
    if settings.cookies_from_browser not in COOKIE_SOURCES:
        raise AppError("INVALID_SETTINGS", "Unsupported browser for cookies", 422)
    if not LANGS_RE.match(settings.subtitles.langs):
        raise AppError("INVALID_SETTINGS", "Invalid subtitle language list", 422)
    if settings.network.rate_limit:
        settings.network.rate_limit = settings.network.rate_limit.strip()
        if not RATE_RE.match(settings.network.rate_limit):
            raise AppError("INVALID_SETTINGS", "Rate limit must look like 2M or 500K", 422)
    return settings


async def load_settings(repo: SettingsRepo, config: Config) -> SettingsModel:
    data = await repo.get_data()
    return normalize_settings(data, config)


async def save_settings(repo: SettingsRepo, config: Config, payload: dict) -> SettingsModel:
    settings = normalize_settings(payload, config)
    await repo.put_data(settings.model_dump())
    return settings
