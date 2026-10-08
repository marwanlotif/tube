from datetime import timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.tables import DownloadRow, SettingsRow, utcnow
from app.domain.enums import Event, Status
from app.domain.state import apply


class DownloadRepo:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def create(self, **fields: Any) -> DownloadRow:
        async with self.sessions.begin() as session:
            row = DownloadRow(**fields)
            session.add(row)
        return row

    async def get(self, download_id: str) -> DownloadRow | None:
        async with self.sessions() as session:
            return await session.get(DownloadRow, download_id)

    async def list_rows(
        self,
        status: Status | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DownloadRow]:
        stmt = select(DownloadRow).order_by(DownloadRow.created_at.desc())
        if status:
            stmt = stmt.where(DownloadRow.status == status.value)
        stmt = stmt.limit(limit).offset(offset)
        async with self.sessions() as session:
            return list((await session.execute(stmt)).scalars().all())

    async def active(self) -> list[DownloadRow]:
        stmt = select(DownloadRow).where(
            DownloadRow.status.in_([s.value for s in Status if s not in {
                Status.COMPLETED, Status.FAILED, Status.CANCELED
            }])
        )
        async with self.sessions() as session:
            return list((await session.execute(stmt)).scalars().all())

    async def transition(self, download_id: str, event: Event, **fields: Any) -> DownloadRow:
        """The only place status is written. Status and fields commit together."""
        async with self.sessions.begin() as session:
            row = await session.get(DownloadRow, download_id)
            if row is None:
                raise KeyError(download_id)
            row.status = apply(Status(row.status), event).value
            for key, value in fields.items():
                setattr(row, key, value)
        return row

    async def update_progress(self, download_id: str, **fields: Any) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(DownloadRow, download_id)
            if row is None:
                return
            for key, value in fields.items():
                setattr(row, key, value)

    async def delete(self, download_id: str) -> None:
        async with self.sessions.begin() as session:
            await session.execute(delete(DownloadRow).where(DownloadRow.id == download_id))

    async def count(self, status: Status | None = None) -> int:
        stmt = select(func.count()).select_from(DownloadRow)
        if status:
            stmt = stmt.where(DownloadRow.status == status.value)
        async with self.sessions() as session:
            return int((await session.execute(stmt)).scalar_one())

    async def stats(self) -> dict:
        week_ago = utcnow() - timedelta(days=7)
        async with self.sessions() as session:
            counts = dict(
                (
                    await session.execute(
                        select(DownloadRow.status, func.count()).group_by(DownloadRow.status)
                    )
                ).all()
            )
            bytes_week = (
                await session.execute(
                    select(func.coalesce(func.sum(DownloadRow.file_size), 0)).where(
                        DownloadRow.status == Status.COMPLETED.value,
                        DownloadRow.finished_at >= week_ago,
                    )
                )
            ).scalar_one()
            total_completed = (
                await session.execute(
                    select(func.count()).where(DownloadRow.status == Status.COMPLETED.value)
                )
            ).scalar_one()
        return {
            "counts": counts,
            "bytes_last_7d": int(bytes_week or 0),
            "completed_total": int(total_completed or 0),
            "active_total": sum(
                counts.get(s.value, 0)
                for s in (
                    Status.QUEUED,
                    Status.EXTRACTING,
                    Status.DOWNLOADING,
                    Status.PROCESSING,
                    Status.VERIFYING,
                )
            ),
        }


class SettingsRepo:
    def __init__(self, sessions: async_sessionmaker):
        self.sessions = sessions

    async def get_data(self) -> dict:
        async with self.sessions() as session:
            row = await session.get(SettingsRow, 1)
            return dict(row.data) if row else {}

    async def put_data(self, data: dict) -> None:
        async with self.sessions.begin() as session:
            row = await session.get(SettingsRow, 1)
            if row is None:
                session.add(SettingsRow(id=1, data=data))
            else:
                row.data = data
