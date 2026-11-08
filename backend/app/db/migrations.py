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

MIGRATIONS: dict[int, Migration] = {}
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
