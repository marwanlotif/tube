from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class DownloadRow(Base):
    __tablename__ = "downloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str | None] = mapped_column(String(64))
    video_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text)
    uploader: Mapped[str | None] = mapped_column(Text)
    thumbnail_name: Mapped[str | None] = mapped_column(String(80))
    duration_s: Mapped[int | None] = mapped_column(Integer)

    mode: Mapped[str] = mapped_column(String(16), default="video")
    status: Mapped[str] = mapped_column(String(16), default="queued")
    format_label: Mapped[str | None] = mapped_column(Text)
    format_selector: Mapped[str | None] = mapped_column(Text)
    container: Mapped[str | None] = mapped_column(String(16))

    output_dir: Mapped[str | None] = mapped_column(Text)
    output_path: Mapped[str | None] = mapped_column(Text)
    temp_path: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(Integer)

    downloaded_bytes: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int | None] = mapped_column(Integer)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    speed: Mapped[float | None] = mapped_column(Float)
    eta_s: Mapped[int | None] = mapped_column(Integer)

    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    log_tail: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    job_spec: Mapped[dict] = mapped_column(JSON, default=dict)
    pid: Mapped[int | None] = mapped_column(Integer)
    pid_started_ticks: Mapped[int | None] = mapped_column(Integer)
    resumable: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_downloads_status", "status"),
        Index("ix_downloads_created", created_at.desc()),
    )


class SettingsRow(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
