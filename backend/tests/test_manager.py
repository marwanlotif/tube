import asyncio
import json
import shutil
import uuid
from pathlib import Path

import pytest

from app.db.engine import init_db, make_engine, make_sessionmaker
from app.db.repos import DownloadRepo, SettingsRepo
from app.domain.enums import Event, Status
from app.services.download_manager import DownloadManager
from app.services.events import EventBus
from app.services.extractor import Extractor
from app.services.runner import Runner
from tests.conftest import FAKE_YTDLP, FAKES

URL = "https://example.com/watch?v=abc123"


class CountingRunner(Runner):
    def __init__(self, ffmpeg: str | None = shutil.which("ffmpeg") or "/bin/true"):
        super().__init__(str(FAKE_YTDLP), ffmpeg)
        self.starts: list[str] = []

    async def start(self, spec, job_id):
        self.starts.append(job_id)
        return await super().start(spec, job_id)


@pytest.fixture
async def harness(config, fake_env):
    config.ensure_dirs()
    engine = make_engine(config)
    await init_db(engine)
    sessions = make_sessionmaker(engine)
    repo = DownloadRepo(sessions)
    runner = CountingRunner()
    extractor = Extractor(str(FAKE_YTDLP), config.thumbnails_dir)
    manager = DownloadManager(
        config, repo, SettingsRepo(sessions), extractor, runner=runner, events=EventBus()
    )
    yield repo, manager, runner
    await manager.stop()
    await engine.dispose()


async def _queued_job(
    repo: DownloadRepo, output_dir: Path, row: dict | None = None, **spec
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid.uuid4())
    await repo.create(
        id=job_id,
        url=URL,
        status=Status.QUEUED.value,
        output_dir=str(output_dir),
        job_spec={
            "url": URL,
            "mode": "video",
            "output_dir": str(output_dir),
            "filename_template": "%(title)s.%(ext)s",
            "selector": "18",
            "preset_key": "best_1080",
            **spec,
        },
        **(row or {}),
    )
    return job_id


def _deferred(**extra) -> dict:
    """A playlist item: no selector yet, formats are resolved when the job runs."""
    return {"selector": None, "revalidate": True, **extra}


async def test_claim_succeeds_once_and_only_from_queued(harness, media_roots):
    repo, _, _ = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube")

    first, second = await asyncio.gather(
        repo.claim(job_id, Event.SPAWN), repo.claim(job_id, Event.SPAWN)
    )
    winners = [row for row in (first, second) if row is not None]
    assert len(winners) == 1
    assert winners[0].status == Status.DOWNLOADING.value
    assert await repo.claim(job_id, Event.START) is None


async def test_duplicate_queue_entries_run_the_job_once(harness, media_roots):
    repo, manager, runner = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube")

    # Two workers picking up the same id at the same moment.
    await asyncio.gather(manager._run(job_id), manager._run(job_id))

    assert runner.starts == [job_id]
    row = await repo.get(job_id)
    assert row.status == Status.COMPLETED.value
    assert row.error_code is None


async def test_job_canceled_while_queued_is_never_started(harness, media_roots):
    repo, manager, runner = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube")

    await manager.cancel(job_id)
    await manager._run(job_id)

    assert runner.starts == []
    assert (await repo.get(job_id)).status == Status.CANCELED.value


async def test_cancel_then_retry_while_queued_completes_once(harness, media_roots):
    repo, manager, runner = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube")
    await manager.enqueue(job_id)
    await manager.cancel(job_id)
    await manager.retry(job_id)  # the id is now in the queue twice
    assert manager.queue.qsize() == 2

    await manager.start()
    await asyncio.wait_for(manager.queue.join(), timeout=15)

    assert runner.starts == [job_id]
    assert (await repo.get(job_id)).status == Status.COMPLETED.value


async def test_deferred_item_resolves_formats_and_fills_in_details(harness, media_roots):
    repo, manager, runner = harness
    job_id = await _queued_job(
        repo,
        media_roots / "Videos" / "Tube",
        row={"title": "From listing", "video_id": "abc123", "site": "Youtube"},
        **_deferred(),
    )

    await manager._run(job_id)

    row = await repo.get(job_id)
    assert row.status == Status.COMPLETED.value, row.error_message
    assert runner.starts == [job_id]
    assert row.format_selector == "137+140"
    assert row.title == "Test Video"
    assert row.uploader == "Tester"
    assert row.duration_s == 120
    assert row.site == "Test"
    assert row.job_spec["revalidate"] is False


async def test_audio_item_keeps_its_target_container(harness, media_roots):
    repo, manager, _ = harness
    job_id = await _queued_job(
        repo,
        media_roots / "Music" / "Tube",
        row={"mode": "audio", "container": "opus"},
        **_deferred(mode="audio", preset_key="audio", audio_format="opus"),
    )
    await manager._run(job_id)
    row = await repo.get(job_id)
    assert row.status == Status.COMPLETED.value, row.error_message
    assert row.container == "opus"


async def test_deferred_item_with_unfit_preset_fails_clearly(
    harness, media_roots, fake_env, tmp_path
):
    audio_only = json.loads((FAKES / "info.json").read_text())
    audio_only["formats"] = [f for f in audio_only["formats"] if f["format_id"] == "140"]
    info_path = tmp_path / "audio_only.json"
    info_path.write_text(json.dumps(audio_only))
    fake_env.setenv("FAKE_YTDLP_INFO", str(info_path))
    repo, manager, runner = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube", **_deferred())

    await manager._run(job_id)

    row = await repo.get(job_id)
    assert row.status == Status.FAILED.value
    assert row.error_code == "PRESET_UNAVAILABLE"
    assert runner.starts == []


async def test_merge_without_ffmpeg_fails_before_spawning(harness, media_roots):
    repo, manager, runner = harness
    manager.runner = no_ffmpeg = CountingRunner(ffmpeg=None)
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube", **_deferred())

    await manager._run(job_id)

    row = await repo.get(job_id)
    assert row.status == Status.FAILED.value
    assert row.error_code == "FFMPEG_MISSING"
    assert no_ffmpeg.starts == [] and runner.starts == []


async def test_missing_selector_without_revalidation_is_invalid(harness, media_roots):
    repo, manager, runner = harness
    job_id = await _queued_job(repo, media_roots / "Videos" / "Tube", selector=None)
    await manager._run(job_id)
    row = await repo.get(job_id)
    assert row.status == Status.FAILED.value
    assert row.error_code == "SPEC_INVALID"
    assert runner.starts == []
