from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

AudioFormat = Literal["mp3", "m4a", "flac", "wav", "opus"]


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


# Response models whose defaults are always present in the payload; marking them required
# keeps generated client types precise (e.g. ``kind`` can be used to narrow the union).
_RESPONSE_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)


class VideoInfoOut(BaseModel):
    model_config = _RESPONSE_CONFIG

    kind: Literal["video"] = "video"
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
    playlist_hint: bool = False


class CollectionEntryOut(BaseModel):
    id: str
    index: int
    title: str
    url: str | None = None
    duration_s: int | None = None
    kind: Literal["video", "collection"]
    available: bool
    reason: str | None = None


class CollectionInfoOut(BaseModel):
    model_config = _RESPONSE_CONFIG

    kind: Literal["collection"] = "collection"
    id: str
    collection_type: Literal["playlist", "channel"]
    title: str
    uploader: str | None = None
    site: str | None = None
    webpage_url: str
    thumbnail_url: str | None = None
    total: int | None = None
    truncated: bool = False
    max_entries: int
    entries: list[CollectionEntryOut]
    presets: list[PresetOut]


ProbeOut = Annotated[VideoInfoOut | CollectionInfoOut, Field(discriminator="kind")]


class VideoInfoRequest(BaseModel):
    url: str
    playlist: bool = False


class DownloadCreate(BaseModel):
    url: str
    preset: str | None = None
    video_id: str | None = None
    audio_id: str | None = None
    mode: Literal["video", "audio"] = "video"
    audio_format: AudioFormat | None = None
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
    collection_id: str | None = None
    playlist_index: int | None = None


class DownloadList(BaseModel):
    items: list[DownloadOut]
    total: int


class CollectionCreate(BaseModel):
    url: str
    # Ids from the listing returned by /api/videos/info; the server maps them back to
    # entries itself and never downloads a URL supplied by the client.
    entry_ids: list[str] = Field(min_length=1, max_length=5000)
    mode: Literal["video", "audio"] = "video"
    preset: str | None = None
    audio_format: AudioFormat | None = None
    subtitles: bool | None = None
    subtitle_langs: str | None = None
    subfolder: bool = True
    skip_existing: bool = True


class CollectionOut(BaseModel):
    model_config = _RESPONSE_CONFIG

    id: str
    url: str
    collection_type: Literal["playlist", "channel"]
    title: str | None = None
    uploader: str | None = None
    site: str | None = None
    thumbnail_url: str | None = None
    mode: Literal["video", "audio"]
    preset_key: str | None = None
    output_dir: str | None = None
    entry_total: int
    item_total: int
    counts: dict[str, int] = Field(default_factory=dict)
    active_total: int = 0
    completed_total: int = 0
    failed_total: int = 0  # failed, canceled or interrupted: everything retry can pick up
    progress: float = 0.0
    created_at: datetime


class CollectionList(BaseModel):
    items: list[CollectionOut]
    total: int


class CollectionSkipped(BaseModel):
    not_found: int = 0
    unavailable: int = 0
    blocked: int = 0
    already_downloaded: int = 0


class CollectionCreated(BaseModel):
    model_config = _RESPONSE_CONFIG

    collection: CollectionOut
    created: int
    skipped: CollectionSkipped


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
