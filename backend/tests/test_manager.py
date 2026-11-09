import asyncio
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
from tests.conftest import FAKE_YTDLP

URL = "https://example.com/watch?v=abc123"


class CountingRunner(Runner):
    def __init__(self):
        super().__init__(str(FAKE_YTDLP), None)
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


async def _queued_job(repo: DownloadRepo, output_dir: Path, **spec) -> str:
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
    )
    return job_id


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


async def test_retry_revalidates_with_the_jobs_browser_cookies(
    harness, media_roots, fake_env, tmp_path
):
    repo, manager, runner = harness
    log_path = tmp_path / "argv.log"
    fake_env.setenv("FAKE_ARGV_LOG", str(log_path))
    job_id = await _queued_job(
        repo, media_roots / "Videos" / "Tube", cookies_from_browser="firefox"
    )

    fake_env.setenv("FAKE_EXIT", "1")
    await manager._run(job_id)
    assert (await repo.get(job_id)).status == Status.FAILED.value

    fake_env.delenv("FAKE_EXIT")
    await manager.retry(job_id)  # re-extracts the video before downloading again
    await manager._run(job_id)

    row = await repo.get(job_id)
    assert row.status == Status.COMPLETED.value
    assert row.job_spec["revalidate"] is False
    assert runner.starts == [job_id, job_id]
    lines = log_path.read_text().splitlines()
    probes = [line for line in lines if " -J " in f" {line} "]
    assert len(probes) == 1
    assert "--cookies-from-browser firefox" in probes[0]
    assert all("--cookies-from-browser firefox" in line for line in lines)
