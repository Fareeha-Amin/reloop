"""Recycling fallback against the database. SIMULATED: an admin confirms on the
recycler's behalf, and the settlement moves no money (Phase 4 adds wallets)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Actor, CommissionSource, DonationAction, WalletTxnType
from app.domain import recycling as rules
from app.models import Donation, Recycling, User, WasteCollector
from app.services import commission, transitions, wallet
from app.services.errors import Conflict


def find_recycler(db: Session, donation: Donation) -> tuple[WasteCollector, float] | None:
    collectors = {
        c.id: c
        for c in db.scalars(
            select(WasteCollector).where(
                WasteCollector.is_active.is_(True),
                WasteCollector.categories_accepted.contains([donation.category]),
            )
        )
    }
    found = rules.select_recycler(
        donation.category,
        donation.pickup_latitude,
        donation.pickup_longitude,
        [
            rules.CollectorFacts(
                collector_id=c.id,
                latitude=c.latitude,
                longitude=c.longitude,
                is_active=c.is_active,
                categories_accepted=frozenset(c.categories_accepted),
            )
            for c in collectors.values()
        ],
    )
    if found is None:
        return None
    facts, distance = found
    return collectors[facts.collector_id], distance


def redirect(
    db: Session,
    donation: Donation,
    actor: Actor,
    user: User,
    now: datetime,
    reason: str | None = None,
) -> None:
    """Consent to recycle comes only from the donor (at escalation) or an admin (with a
    reason); the lifecycle table enforces which. If no recycler can take it, the
    donation goes straight to the admin queue — never silently anywhere else."""
    transitions.apply(
        db, donation, DonationAction.REDIRECT_TO_RECYCLING, actor, now, user=user, reason=reason
    )
    found = find_recycler(db, donation)
    if found is None:
        transitions.apply(db, donation, DonationAction.NO_RECYCLER, Actor.SYSTEM, now)
        return
    collector, distance = found
    db.add(
        Recycling(
            donation_id=donation.id,
            collector_id=collector.id,
            distance_km=distance,
            rate_per_kg=collector.rate_per_kg,
            assigned_by_id=user.id,
            created_at=now,
        )
    )


def current(db: Session, donation_id) -> Recycling | None:
    """The most recent assignment; earlier ones were abandoned (stalled and redirected)."""
    return db.scalar(
        select(Recycling)
        .where(Recycling.donation_id == donation_id)
        .order_by(Recycling.created_at.desc())
        .limit(1)
    )


def confirm(db: Session, donation: Donation, admin: User, reason: str, now: datetime) -> Recycling:
    transitions.ensure_edge(donation, DonationAction.CONFIRM_RECYCLED, Actor.ADMIN)
    assignment = current(db, donation.id)
    if assignment is None or assignment.confirmed_at is not None:
        # A WASTE_REDIRECTED donation always has an open assignment; this is a data fault.
        raise Conflict("This donation has no open recycling assignment.")
    s = rules.settle(donation.category, donation.quantity, assignment.rate_per_kg)
    assignment.weight_per_item_kg = s.weight_per_item_kg
    assignment.estimated_mass_kg = s.estimated_mass_kg
    assignment.gross_value = s.gross_value
    assignment.platform_fee_pct = s.platform_fee_pct
    assignment.platform_fee = s.platform_fee
    assignment.donor_credit = s.donor_credit
    assignment.confirmed_at = now
    assignment.confirmed_by_id = admin.id
    wallet.record(
        db, donation.donor_id, WalletTxnType.RECYCLING_CREDIT, s.donor_credit, now,
        reference_recycling_id=assignment.id, note="Recycling settlement.",
    )
    commission.record(db, CommissionSource.RECYCLING, assignment.id, s.platform_fee, now)
    transitions.apply(
        db, donation, DonationAction.CONFIRM_RECYCLED, Actor.ADMIN, now, user=admin, reason=reason
    )
    return assignment
