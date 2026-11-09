"""Forward-only schema migrations keyed on SQLite's ``PRAGMA user_version``.

A fresh database is created straight from the current table metadata and stamped with
``SCHEMA_VERSION``. An existing database is upgraded one version at a time; each step runs
inside the caller's transaction, so a failed step leaves the previous version intact.
"""

import logging
from collections.abc import Callable

from sqlalchemy import Connection, inspect

from app.db.tables import Base

log = logging.getLogger(__name__)

Migration = Callable[[Connection], None]

# Databases created before migrations existed were stamped with version 1.
BASELINE_VERSION = 1


def _v2_collections(conn: Connection) -> None:
    """Group playlist/channel items under a collection.

    The DDL is frozen here rather than derived from the models, so later model changes
    cannot alter what this step does. It must match a fresh ``create_all`` exactly.
    """
    for statement in (
        """
        CREATE TABLE collections (
            id VARCHAR(36) NOT NULL,
            url TEXT NOT NULL,
            source_id TEXT,
            collection_type VARCHAR(16) NOT NULL,
            title TEXT,
            uploader TEXT,
            site VARCHAR(64),
            thumbnail_name VARCHAR(80),
            mode VARCHAR(16) NOT NULL,
            preset_key VARCHAR(32),
            output_dir TEXT,
            entry_total INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            PRIMARY KEY (id)
        )
        """,
        "CREATE INDEX ix_collections_created ON collections (created_at DESC)",
        # SQLite allows a REFERENCES clause on ADD COLUMN when the default is NULL.
        (
            "ALTER TABLE downloads ADD COLUMN collection_id VARCHAR(36) "
            "REFERENCES collections (id) ON DELETE SET NULL"
        ),
        "ALTER TABLE downloads ADD COLUMN playlist_index INTEGER",
        "CREATE INDEX ix_downloads_collection ON downloads (collection_id, playlist_index)",
    ):
        conn.exec_driver_sql(statement)


MIGRATIONS: dict[int, Migration] = {2: _v2_collections}
SCHEMA_VERSION = max(MIGRATIONS, default=BASELINE_VERSION)


class SchemaTooNew(RuntimeError):
    pass


def current_version(conn: Connection) -> int:
    return int(conn.exec_driver_sql("PRAGMA user_version").scalar_one())


def _stamp(conn: Connection, version: int) -> None:
    # PRAGMA does not accept bound parameters; the value is always an int we control.
    conn.exec_driver_sql(f"PRAGMA user_version={int(version)}")


def migrate(
    conn: Connection,
    migrations: dict[int, Migration] | None = None,
    latest: int | None = None,
) -> int:
    """Bring the schema to ``latest`` and return the resulting version.

    Must be called on a connection with no statements issued yet in its transaction.
    """
    migrations = MIGRATIONS if migrations is None else migrations
    latest = SCHEMA_VERSION if latest is None else latest

    # Python's sqlite3 driver only opens a transaction implicitly before DML, so DDL would
    # otherwise autocommit statement by statement. IMMEDIATE also takes the write lock up
    # front, serialising two processes that start against the same database.
    conn.exec_driver_sql("BEGIN IMMEDIATE")

    if not inspect(conn).has_table("downloads"):
        Base.metadata.create_all(conn)
        _stamp(conn, latest)
        return latest

    version = max(current_version(conn), BASELINE_VERSION)
    if version > latest:
        raise SchemaTooNew(
            f"Database schema version {version} is newer than this build supports ({latest})"
        )
    for target in range(version + 1, latest + 1):
        step = migrations.get(target)
        if step is None:
            raise RuntimeError(f"No migration registered for schema version {target}")
        log.info("migrating database schema to version %s", target)
        step(conn)
        _stamp(conn, target)
    return latest
