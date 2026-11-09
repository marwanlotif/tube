from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VID_DWN_", env_file=REPO_ROOT / ".env", extra="ignore"
    )

    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = Path.home() / ".local" / "share" / "vid-dwn"
    allowed_media_roots: str = ""
    ytdlp_path: str | None = None
    ffmpeg_path: str | None = None
    max_concurrent_downloads: int = 1
    max_collection_entries: int = Field(default=500, ge=1, le=5000)
    open_browser: bool = True
    dev_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "localhost,127.0.0.1,[::1],testserver"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "vid-dwn.sqlite3"

    @property
    def thumbnails_dir(self) -> Path:
        return self.data_dir / "thumbnails"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def frontend_dist(self) -> Path:
        return REPO_ROOT / "frontend" / "dist"

    @property
    def media_roots(self) -> list[Path]:
        if self.allowed_media_roots.strip():
            raw = self.allowed_media_roots.split(":")
        else:
            raw = [str(Path.home() / "Videos"), str(Path.home() / "Music"),
                   str(Path.home() / "Downloads")]
        return [Path(p).expanduser().resolve() for p in raw if p.strip()]

    @property
    def dev_origin_list(self) -> list[str]:
        return [o.strip() for o in self.dev_origins.split(",") if o.strip()]

    @property
    def host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.thumbnails_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)
        for root in self.media_roots:
            if root.name in {"Videos", "Music", "Downloads"}:
                (root / "VidDwn").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_config() -> Config:
    return Config()
