import pytest

from app.db.engine import init_db, make_engine, make_sessionmaker
from app.db.repos import CollectionRepo, DownloadRepo
from app.domain.enums import Status


@pytest.fixture
async def repos(config):
    config.ensure_dirs()
    engine = make_engine(config)
    await init_db(engine)
    sessions = make_sessionmaker(engine)
    yield DownloadRepo(sessions), CollectionRepo(sessions)
    await engine.dispose()


def _item(job_id: str, index: int, status: Status = Status.QUEUED, **extra) -> dict:
    return {
        "id": job_id,
        "url": f"https://x.test/{job_id}",
        "video_id": job_id,
        "site": "Youtube",
        "mode": "video",
        "status": status.value,
        "playlist_index": index,
        "job_spec": {},
        **extra,
    }


def _collection(collection_id: str = "col-1", **extra) -> dict:
    return {
        "id": collection_id,
        "url": "https://x.test/list",
        "collection_type": "playlist",
        "title": "List",
        "mode": "video",
        "entry_total": 3,
        **extra,
    }


async def test_collection_and_items_are_created_together(repos):
    downloads, collections = repos
    row, items = await collections.create_with_items(
        _collection(), [_item("a", 1), _item("b", 2), _item("c", 3)]
    )
    assert row.id == "col-1"
    assert {i.collection_id for i in items} == {"col-1"}
    assert (await downloads.get("b")).collection_id == "col-1"


async def test_a_failing_item_rolls_back_the_whole_collection(repos):
    downloads, collections = repos
    with pytest.raises(Exception):  # noqa: B017 - duplicate primary key from the driver
        await collections.create_with_items(_collection(), [_item("a", 1), _item("a", 2)])
    assert await collections.get("col-1") is None
    assert await downloads.get("a") is None


async def test_listing_filters_items_and_standalone_downloads(repos):
    downloads, collections = repos
    await downloads.create(**{**_item("solo", 0), "playlist_index": None})
    await collections.create_with_items(_collection(), [_item("b", 2), _item("a", 1)])

    items = await downloads.list_rows(collection_id="col-1")
    assert [r.id for r in items] == ["a", "b"]  # playlist order, not insertion order
    standalone = await downloads.list_rows(standalone=True)
    assert [r.id for r in standalone] == ["solo"]
    assert await downloads.count(collection_id="col-1") == 2
    assert await downloads.count(standalone=True) == 1
    assert await downloads.count() == 3


async def test_active_rows_come_back_in_creation_then_playlist_order(repos):
    downloads, collections = repos
    await collections.create_with_items(
        _collection(), [_item("x1", 1), _item("x2", 2), _item("x3", 3, Status.COMPLETED)]
    )
    assert [r.id for r in await downloads.active()] == ["x1", "x2"]


async def test_existing_videos_matches_completed_and_in_progress_in_the_same_mode(repos):
    downloads, collections = repos
    await collections.create_with_items(
        _collection(),
        [
            _item("done", 1, Status.COMPLETED),
            _item("running", 2, Status.DOWNLOADING),
            _item("broken", 3, Status.FAILED),
            _item("other-mode", 4, Status.COMPLETED, mode="audio"),
        ],
    )
    found = await downloads.existing_videos(
        "video", ["done", "running", "broken", "other-mode", "missing"]
    )
    assert found == {("Youtube", "done"), ("Youtube", "running")}
    assert await downloads.existing_videos("video", []) == set()


async def test_summary_counts_statuses_and_in_progress_amount(repos):
    _, collections = repos
    await collections.create_with_items(
        _collection(),
        [
            _item("a", 1, Status.COMPLETED, progress=100.0),
            _item("b", 2, Status.DOWNLOADING, progress=40.0),
            _item("c", 3, Status.FAILED, progress=70.0),
        ],
    )
    summary = await collections.summary("col-1")
    assert summary.counts == {"completed": 1, "downloading": 1, "failed": 1}
    assert summary.item_total == 3
    assert summary.active_progress == 40.0  # failed items do not count as progress
    assert summary.count(Status.COMPLETED, Status.FAILED) == 2
    assert await collections.summary("missing") is None


async def test_summaries_are_newest_first(repos):
    _, collections = repos
    await collections.create_with_items(_collection("old"), [_item("o", 1)])
    await collections.create_with_items(_collection("new"), [])
    summaries = await collections.summaries()
    assert [s.row.id for s in summaries] == ["new", "old"]
    assert summaries[0].item_total == 0
    assert await collections.count() == 2


async def test_ids_in_collection_by_status(repos):
    downloads, collections = repos
    await collections.create_with_items(
        _collection(),
        [_item("q", 1), _item("f", 2, Status.FAILED), _item("c", 3, Status.CANCELED)],
    )
    retryable = await downloads.ids_in_collection("col-1", {Status.FAILED, Status.CANCELED})
    assert retryable == ["f", "c"]


async def test_delete_removes_items_and_empty_collections_only(repos):
    downloads, collections = repos
    await collections.create_with_items(_collection(), [_item("a", 1)])
    assert await collections.delete_if_empty("col-1") is False

    await downloads.delete("a")
    assert await collections.delete_if_empty("col-1") is True
    assert await collections.get("col-1") is None

    await collections.create_with_items(_collection("col-2"), [_item("b", 1)])
    await collections.delete("col-2")
    assert await collections.get("col-2") is None
    assert await downloads.get("b") is None
