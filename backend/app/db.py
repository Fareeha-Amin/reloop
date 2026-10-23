"""SQLAlchemy engine, session dependency and declarative base (synchronous sessions)."""

import uuid
from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from typing import ClassVar

from sqlalchemy import DateTime, Engine, MetaData, String, create_engine, event, func, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import TypeDecorator

from app.config import get_settings

# Deterministic constraint names, so migrations can refer to them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    """UUID primary keys, so donation and organisation IDs cannot be guessed or counted."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AppendOnlyViolation(Exception):
    pass


class AppendOnly:
    """Rows of this model are inserted once and never deleted (non-negotiable 3).

    Columns named in __write_once__ may be set exactly once, from NULL: an offer's
    response, a recycling's settlement. Filling an empty field is not overwriting it.
    Every other column is immutable after insert.

    Enforced on every ORM flush by the listeners below, deliberately not by database
    triggers (consistent with the decision against CHECK constraints repeating rules).
    App code issues no bulk UPDATE or DELETE, which would bypass the ORM; a test checks.
    """

    __write_once__: ClassVar[frozenset[str]] = frozenset()


@event.listens_for(AppendOnly, "before_update", propagate=True)
def _refuse_overwrite(mapper, connection, target) -> None:
    state = inspect(target)
    for attr in mapper.column_attrs:
        history = state.attrs[attr.key].history
        if not history.added:
            continue
        name = f"{type(target).__name__}.{attr.key}"
        if attr.key not in target.__write_once__:
            raise AppendOnlyViolation(f"{name} is immutable.")
        # The previous value must be known and NULL. An unloaded (unknown) previous
        # value is refused rather than assumed empty.
        if not history.deleted or any(v is not None for v in history.deleted):
            raise AppendOnlyViolation(f"{name} is write-once and already set (or was not loaded).")


@event.listens_for(AppendOnly, "before_delete", propagate=True)
def _refuse_delete(mapper, connection, target) -> None:
    raise AppendOnlyViolation(f"{type(target).__name__} rows are never deleted.")


class StrEnumType(TypeDecorator):
    """A VARCHAR column whose values must belong to a StrEnum from app.constants.

    Validates on write (an unknown value raises before reaching the database) and returns
    enum members on read. No native ENUM type and no CHECK constraint is created.
    """

    impl = String(32)
    cache_ok = True

    def __init__(self, enum_cls: type[StrEnum]) -> None:
        super().__init__()
        self.enum_cls = enum_cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self.enum_cls(value).value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_cls(value)


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request. Services commit explicitly."""
    with Session(get_engine()) as session:
        yield session
