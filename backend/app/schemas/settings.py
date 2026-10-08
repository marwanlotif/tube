from pydantic import BaseModel, Field


class VideoSettings(BaseModel):
    max_height: int = Field(default=1080, ge=144, le=4320)
    prefer_codec: str = "h264"
    container: str = "mp4"


class AudioSettings(BaseModel):
    format: str = "mp3"
    quality: str = "0"


class SubtitleSettings(BaseModel):
    enabled: bool = False
    langs: str = "en"
    auto: bool = False
    embed: bool = False


class NetworkSettings(BaseModel):
    fragments: int = Field(default=4, ge=1, le=16)
    rate_limit: str | None = None
    retries: int = Field(default=10, ge=0, le=50)
    socket_timeout: int = Field(default=30, ge=5, le=120)


class SettingsModel(BaseModel):
    video_dir: str
    audio_dir: str
    filename_template: str
    video: VideoSettings = Field(default_factory=VideoSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    subtitles: SubtitleSettings = Field(default_factory=SubtitleSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    cookies_from_browser: str | None = None
    max_concurrent_downloads: int = Field(default=1, ge=1, le=4)


COOKIE_SOURCES = {
    None,
    "",
    "firefox",
    "chrome",
    "chromium",
    "brave",
    "edge",
    "opera",
    "vivaldi",
    "safari",
}
AUDIO_FORMATS = {"mp3", "m4a", "flac", "wav", "opus"}


class SettingsUpdate(SettingsModel):
    pass
