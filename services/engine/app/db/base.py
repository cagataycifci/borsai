"""SQLAlchemy declarative base and shared column types."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Stores timezone-aware UTC datetimes; returns them tz-aware on load.

    SQLite has no native tz support, so we normalize to UTC on the way in and
    re-attach UTC on the way out to avoid naive/aware comparison bugs.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def timestamp_column():
    """A created/updated UTC timestamp column defaulting to now()."""
    return mapped_column(UTCDateTime, default=utcnow, nullable=False)


class Base(DeclarativeBase):
    pass
