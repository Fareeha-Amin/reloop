"""Assemble a donation's history for the donor and for admins."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Donation, Match, Recycling, StatusEvent
from app.schemas.timeline import (
    EventOut,
    HandoverOut,
    OfferHistoryOut,
    RecyclingOut,
    SettlementOut,
    TimelineOut,
)


def build(db: Session, donation: Donation, for_admin: bool) -> TimelineOut:
    events = db.scalars(
        select(StatusEvent).where(StatusEvent.donation_id == donation.id).order_by(StatusEvent.id)
    )
    matches = db.scalars(
        select(Match)
        .where(Match.donation_id == donation.id)
        .options(selectinload(Match.organization), selectinload(Match.handover))
        .order_by(Match.offered_at, Match.rank)
    )
    recyclings = db.scalars(
        select(Recycling)
        .where(Recycling.donation_id == donation.id)
        .options(selectinload(Recycling.collector))
        .order_by(Recycling.created_at)
    )
    return TimelineOut(
        events=[
            EventOut(
                at=e.created_at,
                from_state=e.from_state,
                to_state=e.to_state,
                action=e.action,
                actor=e.actor,
                cause=e.cause,
                reason=e.reason if for_admin else None,
            )
            for e in events
        ],
        offers=[
            OfferHistoryOut(
                match_id=m.id,
                organization_id=m.organization_id,
                organization_name=m.organization.name,
                rank=m.rank,
                offered_by=m.offered_by,
                offered_at=m.offered_at,
                expires_at=m.expires_at,
                response=m.response,
                reason_code=m.reason_code,
                note=m.note if for_admin else None,
                responded_at=m.responded_at,
                handover=HandoverOut.model_validate(m.handover) if m.handover else None,
            )
            for m in matches
        ],
        recyclings=[recycling_out(r) for r in recyclings],
    )


def recycling_out(r: Recycling) -> RecyclingOut:
    settlement = None
    if r.confirmed_at is not None:
        settlement = SettlementOut(
            weight_per_item_kg=r.weight_per_item_kg,
            estimated_mass_kg=r.estimated_mass_kg,
            rate_per_kg=r.rate_per_kg,
            gross_value=r.gross_value,
            platform_fee_pct=r.platform_fee_pct,
            platform_fee=r.platform_fee,
            donor_credit=r.donor_credit,
            confirmed_at=r.confirmed_at,
        )
    return RecyclingOut(
        collector_id=r.collector_id,
        collector_name=r.collector.name,
        distance_km=r.distance_km,
        rate_per_kg=r.rate_per_kg,
        assigned_at=r.created_at,
        settlement=settlement,
    )
