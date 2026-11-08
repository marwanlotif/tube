import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Config
from app.core.errors import AppError, redact
from app.db.repos import DownloadRepo, SettingsRepo
from app.db.tables import utcnow
from app.domain.enums import ACTIVE_STATUSES, Event, Status
from app.domain.naming import validate_template
from app.domain.progress import ProgressUpdate, parse_line
from app.domain.state import InvalidTransition
from app.schemas.serialize import download_out
from app.services.events import EventBus
from app.services.extractor import Extractor, VideoInfo
from app.services.runner import RunHandle, Runner
from app.services.settings import load_settings
from app.services.storage import (
    is_within,
    kill_process_group,
    pid_is_alive,
    process_matches,
)

log = logging.getLogger(__name__)


@dataclass
class JobRuntime:
    handle: RunHandle | None = None
    canceled: bool = False
    final_path: str | None = None
    temp_path: str | None = None
    last_flush: float = 0.0
    last_event: float = 0.0
    last_fields: dict = field(default_factory=dict)
    done: asyncio.Event = field(default_factory=asyncio.Event)


class DownloadManager:
    def __init__(
        self,
        config: Config,
        repo: DownloadRepo,
        settings_repo: SettingsRepo,
        extractor: Extractor,
        runner: Runner,
        events: EventBus,
    ):
        self.config = config
        self.repo = repo
        self.settings_repo = settings_repo
        self.extractor = extractor
        self.runner = runner
        self.events = events
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.runtimes: dict[str, JobRuntime] = {}
        self.workers: list[asyncio.Task] = []
        self._stopping = False

    async def start(self) -> None:
        settings = await load_settings(self.settings_repo, self.config)
        await self._recover()
        concurrency = max(1, settings.max_concurrent_downloads)
        self.workers = [
            asyncio.create_task(self._worker(), name=f"download-worker-{i}")
            for i in range(concurrency)
        ]
        log.info("download manager started with %s worker(s)", concurrency)

    async def stop(self) -> None:
        self._stopping = True
        for runtime in list(self.runtimes.values()):
            if runtime.handle:
                runtime.canceled = True
                await kill_process_group(runtime.handle.pid, grace=2.0)
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        for row in await self.repo.active():
            if row.status == Status.QUEUED.value:
                continue
            try:
                await self.repo.transition(
                    row.id,
                    Event.INTERRUPT,
                    pid=None,
                    pid_started_ticks=None,
                    speed=None,
                    eta_s=None,
                )
            except (InvalidTransition, KeyError):
                pass
        self.workers.clear()
        log.info("download manager stopped")

    async def enqueue(self, download_id: str) -> None:
        await self.queue.put(download_id)

    async def cancel(self, download_id: str) -> None:
        row = await self.repo.get(download_id)
        if row is None:
            raise AppError("NOT_FOUND", "Download not found", 404)
        if Status(row.status) not in ACTIVE_STATUSES:
            return  # idempotent
        runtime = self.runtimes.get(download_id)
        if runtime is None:
            await self._cancel_without_process(download_id)
            return
        runtime.canceled = True
        if runtime.handle:
            await kill_process_group(runtime.handle.pid)
            try:
                await asyncio.wait_for(runtime.done.wait(), timeout=8)
            except TimeoutError:
                await self._cancel_without_process(download_id)
        else:
            await self._cancel_without_process(download_id)

    async def _cancel_without_process(self, download_id: str) -> None:
        try:
            await self.repo.transition(
                download_id, Event.CANCEL, finished_at=utcnow(), speed=None, eta_s=None,
                pid=None, pid_started_ticks=None,
            )
        except (InvalidTransition, KeyError):
            pass
        await self._emit(download_id)

    async def retry(self, download_id: str) -> None:
        row = await self.repo.get(download_id)
        if row is None:
            raise AppError("NOT_FOUND", "Download not found", 404)
        if Status(row.status) not in {Status.FAILED, Status.CANCELED, Status.INTERRUPTED}:
            raise AppError("INVALID_STATE", "Only failed, canceled or interrupted jobs can retry", 409)
        spec = dict(row.job_spec or {})
        spec["revalidate"] = True
        await self.repo.transition(
            download_id,
            Event.RETRY,
            attempts=row.attempts + 1,
            job_spec=spec,
            error_code=None,
            error_message=None,
            log_tail=None,
            output_path=None,
            pid=None,
            pid_started_ticks=None,
            progress=0.0,
            downloaded_bytes=0,
            total_bytes=None,
            speed=None,
            eta_s=None,
            started_at=None,
            finished_at=None,
        )
        await self._emit(download_id)
        await self.enqueue(download_id)

    async def _worker(self) -> None:
        while not self._stopping:
            download_id = await self.queue.get()
            try:
                await self._run(download_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("worker crashed on %s", download_id)
            finally:
                self.queue.task_done()

    async def _recover(self) -> None:
        rows = await self.repo.active()
        for row in rows:
            status = Status(row.status)
            if status == Status.QUEUED:
                await self.enqueue(row.id)
                continue
            if (
                row.pid
                and pid_is_alive(row.pid, row.pid_started_ticks)
                and process_matches(row.pid, row.id, row.url, row.output_dir or "")
            ):
                log.warning("killing orphaned yt-dlp process %s for %s", row.pid, row.id)
                await kill_process_group(row.pid)
            resumable = bool(row.temp_path and Path(row.temp_path).exists())
            try:
                await self.repo.transition(
                    row.id,
                    Event.INTERRUPT,
                    pid=None,
                    pid_started_ticks=None,
                    speed=None,
                    eta_s=None,
                    resumable=resumable,
                )
            except InvalidTransition:
                pass
        log.info("recovery complete: %s active row(s)", len(rows))

    async def _run(self, download_id: str) -> None:
        # A job id can sit in the queue more than once (e.g. canceled while queued, then
        # retried). Checking and registering without an await in between keeps a second
        # worker from starting it while the first one is still running.
        if download_id in self.runtimes:
            return
        runtime = JobRuntime()
        self.runtimes[download_id] = runtime
        try:
            row = await self.repo.get(download_id)
            if row is None or row.status != Status.QUEUED.value:
                return
            spec = dict(row.job_spec or {})
            revalidate = bool(spec.get("revalidate"))
            if revalidate:
                claimed = await self.repo.claim(download_id, Event.START)
            else:
                claimed = await self.repo.claim(
                    download_id, Event.SPAWN, started_at=utcnow(), pid=None
                )
            if claimed is None:
                return  # canceled or claimed elsewhere since it was queued
            current = Status(claimed.status)
            self._validate_spec(spec)

            if revalidate:
                if runtime.canceled:
                    await self._finish_canceled(download_id, runtime, current)
                    return
                info: VideoInfo = await self.extractor.extract(
                    spec["url"],
                    force=True,
                    cookies_from_browser=spec.get("cookies_from_browser"),
                )
                resolved = self.extractor.resolve(
                    info,
                    spec.get("preset_key"),
                    spec.get("video_id"),
                    spec.get("audio_id"),
                )
                if resolved is None:
                    if not spec.get("selector"):
                        # Never resolved before: a playlist item whose preset does not fit.
                        raise AppError(
                            "PRESET_UNAVAILABLE", "That quality is not available for this video"
                        )
                    raise AppError("FORMAT_STALE", "No compatible format is available anymore")
                if resolved.requires_merge and not self.runner.ffmpeg:
                    raise AppError("FFMPEG_MISSING", "ffmpeg is needed to merge these formats")
                spec.update(
                    selector=resolved.selector,
                    container=resolved.container,
                    requires_merge=resolved.requires_merge,
                    revalidate=False,
                    extracted_at=datetime.now(UTC).isoformat(),
                )
                spec["resolved"] = {
                    "video_id": resolved.video_id,
                    "audio_id": resolved.audio_id,
                }
                row = await self.repo.transition(
                    download_id,
                    Event.SPAWN,
                    job_spec=spec,
                    format_selector=resolved.selector,
                    format_label=resolved.label,
                    # Audio jobs are labelled by the format they are converted to.
                    container=(
                        spec.get("audio_format") or "mp3"
                        if spec.get("mode") == "audio"
                        else resolved.container
                    ),
                    started_at=utcnow(),
                    # Playlist items are queued from a flat listing; fill in the details.
                    title=info.title,
                    uploader=info.uploader,
                    duration_s=info.duration_s,
                    video_id=info.id or row.video_id,
                    site=info.site or row.site,
                    thumbnail_name=info.thumbnail_name or row.thumbnail_name,
                )
                await self._broadcast(row)
            current = Status.DOWNLOADING

            if runtime.canceled:
                await self._finish_canceled(download_id, runtime, current)
                return

            handle = await self.runner.start(spec, download_id)
            runtime.handle = handle
            await self.repo.update_progress(
                download_id,
                pid=handle.pid,
                pid_started_ticks=getattr(handle, "pid_started_ticks", None),
            )
            stderr_task = asyncio.create_task(handle.pump_stderr())
            await self._consume_stdout(download_id, runtime, handle, current)
            returncode = await handle.proc.wait()
            await stderr_task
            await self._finish(download_id, runtime, handle, returncode)
        except asyncio.CancelledError:
            if runtime.handle:
                await kill_process_group(runtime.handle.pid, grace=1.0)
            raise
        except AppError as exc:
            await self._fail(download_id, exc.code, exc.message, runtime)
        except Exception as exc:
            log.exception("unexpected failure for %s", download_id)
            await self._fail(download_id, "INTERNAL_ERROR", str(exc), runtime)
        finally:
            self.runtimes.pop(download_id, None)
            runtime.done.set()

    async def _consume_stdout(
        self, download_id: str, runtime: JobRuntime, handle: RunHandle, current: Status
    ) -> None:
        import time

        assert handle.proc.stdout is not None
        while True:
            raw = await handle.proc.stdout.readline()
            if not raw:
                break
            parsed = parse_line(raw.decode(errors="replace"))
            if parsed is None:
                continue
            now = time.monotonic()
            if parsed.kind == "dest" and parsed.path:
                runtime.temp_path = parsed.path
                await self.repo.update_progress(
                    download_id, temp_path=parsed.path, resumable=True
                )
            elif parsed.kind == "final" and parsed.path:
                runtime.final_path = parsed.path
            elif parsed.kind == "progress" and parsed.progress:
                update = parsed.progress
                fields = self._progress_fields(update)
                runtime.last_fields = fields
                if update.status == "finished" and current == Status.DOWNLOADING:
                    try:
                        row = await self.repo.transition(
                            download_id, Event.POSTPROCESS, progress=100.0,
                            speed=None, eta_s=None, total_bytes=update.total_bytes,
                        )
                        await self._broadcast(row)
                    except InvalidTransition:
                        pass
                    current = Status.PROCESSING
                if now - runtime.last_flush >= 1.0:
                    runtime.last_flush = now
                    await self.repo.update_progress(download_id, **fields)
                if now - runtime.last_event >= 0.35:
                    runtime.last_event = now
                    row = await self.repo.get(download_id)
                    if row:
                        await self._broadcast(row)

    async def _finish(
        self, download_id: str, runtime: JobRuntime, handle: RunHandle, returncode: int
    ) -> None:
        if runtime.canceled:
            await self._finish_canceled(download_id, runtime, Status.DOWNLOADING)
            return
        if returncode != 0:
            message = handle.stderr_tail.splitlines()[-1] if handle.stderr_tail else "yt-dlp failed"
            await self._fail(
                download_id,
                "DOWNLOAD_FAILED",
                message[:500],
                runtime,
                log_tail=handle.stderr_tail,
            )
            return
        row = await self.repo.get(download_id)
        current = Status(row.status) if row else Status.DOWNLOADING
        if current == Status.DOWNLOADING:
            try:
                await self.repo.transition(download_id, Event.VERIFY)
            except InvalidTransition:
                pass
        elif current == Status.PROCESSING:
            await self.repo.transition(download_id, Event.VERIFY)

        final_path = runtime.final_path or handle.final_path or runtime.temp_path
        spec = (row.job_spec or {}) if row else {}
        output_dir = spec.get("output_dir") or ""
        verified: Path | None = None
        if final_path:
            candidate = Path(final_path).resolve()
            if (
                candidate.is_file()
                and candidate.suffix != ".part"
                and candidate.stat().st_size > 0
                and is_within(candidate, Path(output_dir))
            ):
                verified = candidate

        if verified is None:
            await self._fail(
                download_id,
                "OUTPUT_MISSING",
                "Download finished but the output file could not be verified",
                runtime,
                log_tail=handle.stderr_tail,
            )
            return

        size = verified.stat().st_size
        row = await self.repo.transition(
            download_id,
            Event.VERIFIED,
            output_path=str(verified),
            file_size=size,
            progress=100.0,
            downloaded_bytes=size,
            total_bytes=size,
            speed=None,
            eta_s=None,
            pid=None,
            pid_started_ticks=None,
            resumable=False,
            finished_at=utcnow(),
            error_code=None,
            error_message=None,
        )
        await self._broadcast(row)
        await self.events.broadcast({"type": "stats.updated"})

    async def _finish_canceled(
        self, download_id: str, runtime: JobRuntime, current: Status
    ) -> None:
        try:
            row = await self.repo.transition(
                download_id,
                Event.CANCEL,
                finished_at=utcnow(),
                speed=None,
                eta_s=None,
                pid=None,
                pid_started_ticks=None,
                resumable=bool(runtime.temp_path and Path(runtime.temp_path).exists()),
            )
        except (InvalidTransition, KeyError):
            return
        await self._broadcast(row)
        await self.events.broadcast({"type": "stats.updated"})

    async def _fail(
        self,
        download_id: str,
        code: str,
        message: str,
        runtime: JobRuntime,
        log_tail: str | None = None,
    ) -> None:
        try:
            row = await self.repo.transition(
                download_id,
                Event.FAIL,
                error_code=code,
                error_message=redact(message)[:500],
                log_tail=(log_tail or "")[:8000] or None,
                finished_at=utcnow(),
                speed=None,
                eta_s=None,
                pid=None,
                pid_started_ticks=None,
                resumable=bool(runtime.temp_path and Path(runtime.temp_path).exists()),
            )
        except (InvalidTransition, KeyError):
            return
        await self._broadcast(row)
        await self.events.broadcast({"type": "stats.updated"})

    @staticmethod
    def _progress_fields(update: ProgressUpdate) -> dict:
        return {
            "downloaded_bytes": update.downloaded_bytes,
            "total_bytes": update.total_bytes,
            "progress": update.percent if update.percent is not None else 0.0,
            "speed": update.speed,
            "eta_s": update.eta,
        }

    def _validate_spec(self, spec: dict) -> None:
        output_dir = spec.get("output_dir")
        if not output_dir:
            raise AppError("SPEC_INVALID", "Download output directory is missing")
        path = Path(output_dir)
        if not path.is_absolute() or not path.is_dir():
            raise AppError("SPEC_INVALID", "Download output directory is not available")
        if not any(is_within(path, root) for root in self.config.media_roots):
            raise AppError("SPEC_INVALID", "Download output directory is not allowed")
        validate_template(spec.get("filename_template", ""))
        # A revalidating job resolves its formats when it runs (always the case for
        # playlist items), so only a job that skips extraction needs a selector up front.
        if not spec.get("selector") and not spec.get("revalidate"):
            raise AppError("SPEC_INVALID", "Download format selector is missing")

    async def _broadcast(self, row) -> None:
        await self.events.broadcast({"type": "download.updated", "download": download_out(row)})

    async def _emit(self, download_id: str) -> None:
        row = await self.repo.get(download_id)
        if row:
            await self._broadcast(row)
