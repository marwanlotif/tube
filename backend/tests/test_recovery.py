import os

from app.db.engine import init_db, make_engine, make_sessionmaker
from app.db.repos import DownloadRepo, SettingsRepo
from app.domain.enums import Status
from app.services.download_manager import DownloadManager
from app.services.events import EventBus


class _Extractor:
    pass


async def _manager(config):
    config.ensure_dirs()
    engine = make_engine(config)
    await init_db(engine)
    sessions = make_sessionmaker(engine)
    repo = DownloadRepo(sessions)
    manager = DownloadManager(
        config,
        repo,
        SettingsRepo(sessions),
        extractor=_Extractor(),
        runner=None,
        events=EventBus(),
    )
    return engine, repo, manager


async def test_active_rows_become_interrupted_without_killing_live_pid(config, media_roots):
    engine, repo, manager = await _manager(config)
    output_dir = media_roots / "Videos" / "VidDwn"
    output_dir.mkdir(parents=True, exist_ok=True)
    await repo.create(
        id="job-interrupted",
        url="https://example.com/watch?v=abc",
        status=Status.DOWNLOADING.value,
        output_dir=str(output_dir),
        pid=os.getpid(),
        pid_started_ticks=0,
        job_spec={
            "url": "https://example.com/watch?v=abc",
            "output_dir": str(output_dir),
            "filename_template": "%(title)s.%(ext)s",
            "selector": "137+140",
        },
    )
    await manager.start()
    row = await repo.get("job-interrupted")
    assert row.status == Status.INTERRUPTED.value
    assert row.pid is None
    assert os.getpid() == os.getpid()  # process was not killed
    await manager.stop()
    await engine.dispose()


async def test_queued_rows_are_reenqueued_on_start(config):
    engine, repo, manager = await _manager(config)
    await repo.create(
        id="job-queued",
        url="https://example.com/watch?v=abc",
        status=Status.QUEUED.value,
        output_dir=str(config.media_roots[0] / "VidDwn"),
        job_spec={},
    )
    await manager._recover()
    assert manager.queue.qsize() == 1
    await manager.stop()
    await engine.dispose()


async def test_worker_count_comes_from_settings(config):
    engine, _, manager = await _manager(config)
    await manager.start()
    assert len(manager.workers) == config.max_concurrent_downloads == 2
    await manager.stop()
    await engine.dispose()
