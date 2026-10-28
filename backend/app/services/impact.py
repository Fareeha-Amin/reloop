"""Impact records and totals. Every figure is an ESTIMATE (app.domain.impact).

`record` is called only from app.services.transitions.apply, in the transaction that
moves a donation into COMPLETED or RECYCLED. Records are append-only: nothing recomputes
or edits one.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ImpactOutcome
from app.domain import impact as rules
from app.models import Donation, ImpactRecord, Match


def record(db: Session, donation: Donation, now: datetime, match: Match | None = None) -> ImpactRecord:
    outcome = rules.outcome_for(donation.status)
    if outcome is None:
        raise ValueError(f"A donation in {donation.status.value} has no impact outcome.")
    if outcome == ImpactOutcome.REUSED and match is None:
        raise ValueError("A reused donation needs the accepting offer to name its organisation.")
    est = rules.estimate(donation.category, donation.quantity, outcome)
    row = ImpactRecord(
        donation_id=donation.id,
        donor_id=donation.donor_id,
        organization_id=match.organization_id if outcome == ImpactOutcome.REUSED else None,
        outcome=outcome,
        category=donation.category,
        quantity=donation.quantity,
        mass_kg_per_item=est.mass_kg_per_item,
        mass_kg=est.mass_kg,
        carbon_kg_per_item=est.carbon_kg_per_item,
        carbon_kg=est.carbon_kg,
        created_at=now,
    )
    db.add(row)
    return row


def _contributions(rows) -> list[rules.Contribution]:
    return [
        rules.Contribution(r.outcome, r.quantity, r.mass_kg, r.carbon_kg) for r in rows
    ]


def donor_totals(db: Session, donor_id: uuid.UUID) -> rules.Totals:
    rows = db.scalars(select(ImpactRecord).where(ImpactRecord.donor_id == donor_id)).all()
    return rules.totals(_contributions(rows))


def organisation_totals(db: Session, organization_id: uuid.UUID) -> rules.Totals:
    """Reuse only: recycling is never credited to an organisation."""
    rows = db.scalars(
        select(ImpactRecord).where(ImpactRecord.organization_id == organization_id)
    ).all()
    return rules.totals(_contributions(rows))
