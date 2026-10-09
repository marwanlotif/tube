import asyncio
import hashlib
import ipaddress
import os
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.errors import AppError
from app.domain.urls import assert_public_host

MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_output_dir(raw: str, roots: list[Path], create: bool = True) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise AppError("INVALID_PATH", "Directory must be an absolute path")
    resolved = path.resolve()
    if not any(is_within(resolved, root) for root in roots):
        raise AppError(
            "INVALID_PATH",
            "Directory must be inside an allowed media root",
            details={"allowed_roots": [str(r) for r in roots]},
        )
    if create:
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise AppError("INVALID_PATH", f"Cannot create directory: {exc}") from exc
    if not resolved.is_dir() or not os.access(resolved, os.W_OK):
        raise AppError("INVALID_PATH", "Directory is not writable")
    return resolved


async def disk_info(path: Path) -> tuple[int, int]:
    usage = await asyncio.to_thread(shutil.disk_usage, path)
    return usage.free, usage.total


async def _validate_thumb_host(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ValueError("bad thumbnail scheme")
    await asyncio.to_thread(assert_public_host, parts.hostname or "")


async def fetch_thumbnail(url: str, dest_dir: Path) -> str | None:
    """Fetch once with manual redirects; every hop is revalidated. Returns file name."""
    try:
        current = url
        async with httpx.AsyncClient(follow_redirects=False, timeout=15) as client:
            for _ in range(4):
                await _validate_thumb_host(current)
                async with client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            return None
                        current = urljoin(current, location)
                        continue
                    if response.status_code != 200:
                        return None
                    content_type = response.headers.get("content-type", "")
                    if not content_type.startswith("image/"):
                        return None
                    digest = hashlib.sha1(url.encode()).hexdigest()
                    target = dest_dir / f"{digest}.jpg"
                    written = 0
                    with target.open("wb") as handle:
                        async for chunk in response.aiter_bytes():
                            written += len(chunk)
                            if written > MAX_THUMBNAIL_BYTES:
                                target.unlink(missing_ok=True)
                                return None
                            handle.write(chunk)
                    return target.name
            return None
    except (httpx.HTTPError, OSError, ValueError):
        return None


async def reveal_file(path: str, roots: list[Path]) -> None:
    target = Path(path).resolve()
    if not any(is_within(target, root) for root in roots) or not target.exists():
        raise AppError("INVALID_PATH", "File is outside the allowed media roots")
    try:
        await asyncio.create_subprocess_exec("xdg-open", str(target.parent))
    except OSError as exc:
        raise AppError("REVEAL_FAILED", f"Cannot open file manager: {exc}") from exc


def safe_delete_file(path: str, roots: list[Path]) -> None:
    target = Path(path).resolve()
    if not any(is_within(target, root) for root in roots) or target.name.endswith(".part"):
        raise AppError("INVALID_PATH", "Refusing to delete this file")
    target.unlink(missing_ok=True)


def read_pid_start_ticks(pid: int) -> int | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    try:
        fields = raw[raw.rindex(")") + 2 :].split()
        return int(fields[19])
    except (ValueError, IndexError):
        return None


def process_matches(pid: int, job_id: str, url: str, output_dir: str) -> bool:
    """Require the job id injected into the child environment, not just a cmdline match."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
            errors="replace"
        )
        environ = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return False
    if "yt-dlp" not in cmdline:
        return False
    if f"VID_DWN_JOB_ID={job_id}".encode() not in environ:
        return False
    return url in cmdline and output_dir in cmdline


def pid_is_alive(pid: int, expected_ticks: int | None) -> bool:
    if pid <= 0 or not Path(f"/proc/{pid}").exists():
        return False
    if expected_ticks is None:
        return False
    return read_pid_start_ticks(pid) == expected_ticks


async def kill_process_group(pid: int, grace: float = 5.0) -> None:
    for sig, wait in ((15, grace), (9, 0.0)):
        try:
            os.killpg(os.getpgid(pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        if wait:
            await asyncio.sleep(wait)
            if not Path(f"/proc/{pid}").exists():
                return


def is_public_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )
