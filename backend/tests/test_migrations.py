import pytest
from sqlalchemy import create_engine, inspect, text

from app.db import migrations
from app.db.engine import init_db, make_engine
from app.db.migrations import SCHEMA_VERSION, SchemaTooNew, current_version, migrate

V1_DOWNLOADS = """
CREATE TABLE downloads (
    id VARCHAR(36) PRIMARY KEY,
    url TEXT NOT NULL,
    status VARCHAR(16)
)
"""


@pytest.fixture
def engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite3'}")
    yield engine
    engine.dispose()


def _seed_v1(engine) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(V1_DOWNLOADS)
        conn.exec_driver_sql("INSERT INTO downloads (id, url, status) VALUES ('a', 'u', 'queued')")
        conn.exec_driver_sql("PRAGMA user_version=1")


def _add_note_column(conn) -> None:
    conn.exec_driver_sql("ALTER TABLE downloads ADD COLUMN note TEXT")


def test_fresh_database_is_created_and_stamped(engine):
    with engine.begin() as conn:
        assert migrate(conn) == SCHEMA_VERSION
        assert current_version(conn) == SCHEMA_VERSION
        assert {"downloads", "settings"} <= set(inspect(conn).get_table_names())


def test_existing_database_is_upgraded_step_by_step_and_keeps_rows(engine):
    _seed_v1(engine)
    steps = {2: _add_note_column}
    with engine.begin() as conn:
        assert migrate(conn, steps, latest=2) == 2
    with engine.begin() as conn:
        assert current_version(conn) == 2
        columns = {c["name"] for c in inspect(conn).get_columns("downloads")}
        assert "note" in columns
        assert conn.execute(text("SELECT url FROM downloads WHERE id='a'")).scalar_one() == "u"
        # Running again is a no-op rather than a duplicate-column error.
        assert migrate(conn, steps, latest=2) == 2


def test_unstamped_existing_database_is_treated_as_baseline(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql(V1_DOWNLOADS)
    calls = []
    with engine.begin() as conn:
        migrate(conn, {2: lambda c: calls.append(2)}, latest=2)
        assert calls == [2]


def test_failed_step_rolls_back_and_keeps_previous_version(engine):
    _seed_v1(engine)

    def broken(conn):
        _add_note_column(conn)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"), engine.begin() as conn:
        migrate(conn, {2: broken}, latest=2)
    with engine.begin() as conn:
        assert current_version(conn) == 1
        columns = {c["name"] for c in inspect(conn).get_columns("downloads")}
        assert "note" not in columns


def test_newer_schema_is_refused(engine):
    _seed_v1(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA user_version=99")
    with pytest.raises(SchemaTooNew), engine.begin() as conn:
        migrate(conn)


def test_missing_step_is_reported(engine):
    _seed_v1(engine)
    with pytest.raises(RuntimeError, match="version 2"), engine.begin() as conn:
        migrate(conn, {}, latest=2)


async def test_init_db_runs_migrations(config):
    config.ensure_dirs()
    engine = make_engine(config)
    await init_db(engine)
    await init_db(engine)  # idempotent across restarts
    async with engine.connect() as conn:
        assert await conn.run_sync(current_version) == migrations.SCHEMA_VERSION
    await engine.dispose()
