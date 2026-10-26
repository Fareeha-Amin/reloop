"""The platform's earnings ledger (app.models.Commission): logistics fees and
recycling fees. Pure insert-only; a reversal is a second, negated row."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import CommissionSource
from app.models import Commission

_PAISE = Decimal("0.01")


def record(
    db: Session,
    source: CommissionSource,
    source_id: uuid.UUID,
    amount: Decimal,
    now: datetime,
    note: str | None = None,
) -> Commission:
    entry = Commission(source=source, source_id=source_id, amount=amount, note=note, created_at=now)
    db.add(entry)
    return entry


def total(db: Session) -> Decimal:
    return Decimal(db.scalar(select(func.coalesce(func.sum(Commission.amount), 0)))).quantize(_PAISE)


def recent(db: Session, limit: int, offset: int) -> list[Commission]:
    return list(
        db.scalars(select(Commission).order_by(Commission.created_at.desc()).limit(limit).offset(offset))
    )
