from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FormatOut(BaseModel):
    format_id: str
    ext: str
    kind: str
    vcodec: str | None = None
    acodec: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    tbr: float | None = None
    filesize: int | None = None
    hdr: bool = False
    label: str


class PresetOut(BaseModel):
    key: str
    label: str
    available: bool
    container: str | None = None
    height: int | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    requires_merge: bool = False
    estimated_bytes: int | None = None
    selector_label: str | None = None


class VideoInfoOut(BaseModel):
    id: str
    site: str | None = None
    title: str
    uploader: str | None = None
    duration_s: int | None = None
    webpage_url: str
    thumbnail_url: str | None = None
    is_live: bool = False
    formats: list[FormatOut]
    presets: list[PresetOut]


class VideoInfoRequest(BaseModel):
    url: str


class DownloadCreate(BaseModel):
    url: str
    preset: str | None = None
    video_id: str | None = None
    audio_id: str | None = None
    mode: Literal["video", "audio"] = "video"
    audio_format: Literal["mp3", "m4a", "flac", "wav", "opus"] | None = None
    subtitles: bool | None = None
    subtitle_langs: str | None = None


class DownloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    site: str | None = None
    video_id: str | None = None
    title: str | None = None
    uploader: str | None = None
    thumbnail_url: str | None = None
    duration_s: int | None = None
    mode: str
    status: str
    format_label: str | None = None
    format_selector: str | None = None
    container: str | None = None
    output_dir: str | None = None
    output_path: str | None = None
    file_size: int | None = None
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    progress: float = 0.0
    speed: float | None = None
    eta_s: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    attempts: int = 0
    resumable: bool = False
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class DownloadList(BaseModel):
    items: list[DownloadOut]
    total: int


class StatsOut(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)
    bytes_last_7d: int = 0
    completed_total: int = 0
    active_total: int = 0
    disk_free: int | None = None
    disk_total: int | None = None


class SystemOut(BaseModel):
    ytdlp_version: str | None = None
    ffmpeg_version: str | None = None
    ytdlp_ok: bool = False
    ffmpeg_ok: bool = False
    data_dir: str
    video_dir: str
    audio_dir: str
    allowed_roots: list[str]
    max_concurrent_downloads: int
    log_dir: str
