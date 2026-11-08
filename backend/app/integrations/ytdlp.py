import asyncio
import logging
import os
import shutil
from pathlib import Path

from app.core.config import Config
from app.core.errors import AppError, redact

log = logging.getLogger(__name__)


def _executable(candidate: str | None) -> str | None:
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return str(path)
    return None


class Binaries:
    def __init__(self, config: Config):
        self.config = config
        self.ytdlp = (
            _executable(config.ytdlp_path) if config.ytdlp_path else shutil.which("yt-dlp")
        )
        self.ffmpeg = (
            _executable(config.ffmpeg_path) if config.ffmpeg_path else shutil.which("ffmpeg")
        )
        self.ytdlp_version: str | None = None
        self.ffmpeg_version: str | None = None

    async def probe(self) -> None:
        self.ytdlp_version = await self._version([self.ytdlp, "--version"]) if self.ytdlp else None
        if self.ffmpeg:
            out = await self._run([self.ffmpeg, "-version"])
            self.ffmpeg_version = out.splitlines()[0].strip() if out else None

    @staticmethod
    async def _run(argv: list[str], timeout: float = 10) -> str | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await asyncio.wait_for(proc.communicate(), timeout)
            return out.decode(errors="replace").strip()
        except (TimeoutError, OSError):
            return None

    async def _version(self, argv: list[str]) -> str | None:
        out = await self._run(argv)
        return out.splitlines()[0].strip() if out else None

    def require_ytdlp(self) -> str:
        if not self.ytdlp:
            raise AppError(
                "YTDLP_MISSING",
                "yt-dlp is not installed or not on PATH",
                status=503,
                details={"hint": "Install it with: sudo pacman -S yt-dlp"},
            )
        return self.ytdlp

    def require_ffmpeg(self) -> str:
        if not self.ffmpeg:
            raise AppError(
                "FFMPEG_MISSING",
                "ffmpeg is not installed or not on PATH",
                status=503,
                details={"hint": "Install it with: sudo pacman -S ffmpeg"},
            )
        return self.ffmpeg


def info_argv(
    binary: str,
    url: str,
    cookies_from_browser: str | None = None,
    playlist: bool = False,
    max_entries: int = 500,
) -> list[str]:
    """Probe a link. Single videos come back with formats; playlists and channels come back
    as a flat listing (no per-entry extraction), capped at ``max_entries``.

    ``playlist`` only matters for links that name both a video and a playlist (for example
    ``watch?v=…&list=…``): by default the video wins, as it does for downloads.
    """
    argv = [
        binary,
        "--ignore-config",
        "-J",
        "--flat-playlist",
        "--playlist-items",
        f"1:{max_entries}",
        "--yes-playlist" if playlist else "--no-playlist",
        "--no-warnings",
        "--socket-timeout",
        "20",
    ]
    if cookies_from_browser:
        argv += ["--cookies-from-browser", cookies_from_browser]
    argv.append(url)
    return argv


def download_argv(binary: str, ffmpeg: str | None, spec: dict) -> list[str]:
    network = spec.get("network") or {}
    subtitles = spec.get("subtitles") or {}
    argv = [
        binary,
        "--ignore-config",
        "--no-playlist",
        "--newline",
        "--no-simulate",
        "--progress",
        "--progress-template",
        "download:PROGRESS %(progress)j",
        "--print",
        "before_dl:DEST %(filename)s",
        "--print",
        "after_move:FINAL %(filepath)s",
        "-P",
        spec["output_dir"],
        "-o",
        spec["filename_template"],
        "--no-overwrites",
        "--continue",
        "--retries",
        str(network.get("retries", 10)),
        "--fragment-retries",
        str(network.get("retries", 10)),
        "--socket-timeout",
        str(network.get("socket_timeout", 30)),
        "-N",
        str(network.get("fragments", 4)),
        "-f",
        spec["selector"],
    ]
    if ffmpeg:
        argv += ["--ffmpeg-location", ffmpeg]
    if spec.get("requires_merge"):
        argv += ["--merge-output-format", spec.get("container") or "mkv"]
    rate_limit = network.get("rate_limit")
    if rate_limit:
        argv += ["--limit-rate", str(rate_limit)]
    if spec.get("cookies_from_browser"):
        argv += ["--cookies-from-browser", str(spec["cookies_from_browser"])]
    if spec.get("mode") == "audio":
        argv += [
            "-x",
            "--audio-format",
            spec.get("audio_format") or "mp3",
            "--audio-quality",
            str(spec.get("audio_quality") or "0"),
            "--embed-metadata",
        ]
    else:
        argv += ["--embed-metadata"]
    if subtitles.get("enabled"):
        argv += ["--write-subs", "--sub-langs", subtitles.get("langs") or "en"]
        if subtitles.get("auto"):
            argv += ["--write-auto-subs"]
        if subtitles.get("embed"):
            argv += ["--embed-subs"]
    argv.append(spec["url"])
    return argv


def describe_command(argv: list[str]) -> str:
    """Loggable command with URL query strings stripped."""
    safe: list[str] = []
    for part in argv:
        if part.startswith("http"):
            safe.append(part.split("?")[0])
        else:
            safe.append(redact(part))
    return " ".join(safe)
