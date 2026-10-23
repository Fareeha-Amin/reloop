"""Admin read models: the unroutable queue, ranking runs, recyclers."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DonationAction, DonationStatus
from app.models import Donation, RankingRun, StatusEvent, WasteCollector


@dataclass(frozen=True)
class QueueEntry:
    donation: Donation
    entered_at: datetime
    from_state: DonationStatus
    via: DonationAction


def queue(db: Session) -> list[QueueEntry]:
    """Donations in NEEDS_ADMIN, longest-waiting first, with the transition that put
    each one there (a STALL from some state, or NO_RECYCLER)."""
    entries = []
    for donation in db.scalars(select(Donation).where(Donation.status == DonationStatus.NEEDS_ADMIN)):
        event = db.scalar(
            select(StatusEvent)
            .where(StatusEvent.donation_id == donation.id, StatusEvent.to_state == DonationStatus.NEEDS_ADMIN)
            .order_by(StatusEvent.id.desc())
            .limit(1)
        )
        entries.append(QueueEntry(donation, event.created_at, event.from_state, event.action))
    return sorted(entries, key=lambda e: e.entered_at)


def ranking_runs(db: Session, donation_id: uuid.UUID) -> list[RankingRun]:
    return list(
        db.scalars(select(RankingRun).where(RankingRun.donation_id == donation_id).order_by(RankingRun.created_at))
    )


def recyclers(db: Session) -> list[WasteCollector]:
    return list(db.scalars(select(WasteCollector).order_by(WasteCollector.name)))
