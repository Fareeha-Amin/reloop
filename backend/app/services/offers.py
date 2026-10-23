"""The acceptor side: the inbox of open offers, accept / reject, and the donations the
organisation holds (schedule pickup, confirm receipt).

Address privacy (non-negotiable 10): before acceptance an acceptor sees no address and
no coordinates, only a rounded distance. The precise address is released to the
accepting organisation at ACCEPT (and that release is recorded), and it stays visible
only while the organisation holds the donation (lifecycle.HELD_STATES).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    AddressAccess,
    Actor,
    DonationAction,
    DonationStatus,
    HandoverMode,
    OfferResponse,
    RejectReason,
)
from app.domain import lifecycle, policy
from app.domain.geo import disclose_distance_km, haversine_km
from app.models import Donation, Handover, Match, OrganizationProfile, User
from app.services import audit, matching, organizations, sweeper, transitions
from app.services.actions import ensure_available
from app.services.errors import Conflict, NotFound, Unprocessable

A = DonationAction


@dataclass(frozen=True)
class OfferView:
    match: Match
    donation: Donation
    distance_km: float  # rounded for disclosure

    @property
    def allowed_actions(self) -> frozenset[DonationAction]:
        # An open offer means the donation is MATCHED; the table says what the acceptor may do.
        if not self.match.is_open:
            return frozenset()
        return lifecycle.allowed_actions(self.donation.status, Actor.ACCEPTOR)


def disclosed_distance(org: OrganizationProfile, donation: Donation) -> float:
    return disclose_distance_km(
        haversine_km(org.latitude, org.longitude, donation.pickup_latitude, donation.pickup_longitude)
    )


def inbox(db: Session, user: User, now: datetime) -> list[OfferView]:
    """Open offers, ordered by the donation's queue priority (priority flag and rejection
    boost), then oldest first. Offers already past their expiry are hidden; the sweeper
    or the next answer closes them."""
    org = organizations.get_for_user(db, user)
    rows = db.execute(
        select(Match, Donation)
        .join(Donation, Donation.id == Match.donation_id)
        .where(
            Match.organization_id == org.id,
            Match.response.is_(None),
            Donation.status == DonationStatus.MATCHED,
            Match.expires_at > now,
        )
    ).all()
    declines = matching.declines_by_donation(db, [d.id for _, d in rows])
    config = matching.DEFAULT_CONFIG
    rows.sort(
        key=lambda r: (
            -policy.queue_priority(r[1].is_priority, declines.get(r[1].id, 0), config),
            r[0].offered_at,
        )
    )
    return [OfferView(m, d, disclosed_distance(org, d)) for m, d in rows]


def _own_match(db: Session, org: OrganizationProfile, match_id: uuid.UUID) -> Match:
    match = db.get(Match, match_id)
    if match is None or match.organization_id != org.id:
        raise NotFound("Offer not found.")
    return match


def get_offer(db: Session, user: User, match_id: uuid.UUID) -> OfferView:
    org = organizations.get_for_user(db, user)
    match = _own_match(db, org, match_id)
    donation = db.get(Donation, match.donation_id)
    return OfferView(match, donation, disclosed_distance(org, donation))


def _lock_open_offer(db: Session, user: User, match_id: uuid.UUID, now: datetime):
    org = organizations.get_for_user(db, user)
    match = _own_match(db, org, match_id)
    donation = transitions.lock_donation(db, match.donation_id)
    db.refresh(match)
    if not match.is_open:
        raise Conflict("This offer has already been answered or closed.")
    # Past its expiry but not yet swept: close it now, and say so.
    if sweeper.apply_due(db, donation, now) is not None:
        db.commit()
        raise Conflict("This offer has expired.")
    return org, match, donation


def accept(db: Session, user: User, match_id: uuid.UUID, now: datetime) -> Donation:
    org, match, donation = _lock_open_offer(db, user, match_id, now)
    match.respond(OfferResponse.ACCEPTED, now, responder_id=user.id)
    transitions.apply(db, donation, A.ACCEPT, Actor.ACCEPTOR, now, user=user, match=match)
    audit.record_address_access(db, donation, user, AddressAccess.RELEASED_TO_ACCEPTOR, now, organization=org)
    db.commit()
    return donation


def reject(
    db: Session, user: User, match_id: uuid.UUID, reason_code: RejectReason, note: str | None, now: datetime
) -> Match:
    """Recorded, never deleted. The organisation is excluded from this donation for
    good, and the donation is re-offered or escalated in the same transaction."""
    _, match, donation = _lock_open_offer(db, user, match_id, now)
    match.respond(OfferResponse.REJECTED, now, responder_id=user.id, reason_code=reason_code, note=note)
    transitions.apply(db, donation, A.REJECT, Actor.ACCEPTOR, now, user=user, match=match)
    matching.resolve_re_matching(db, donation, now)
    db.commit()
    return match


# --- Donations the organisation has accepted -------------------------------------------------


@dataclass(frozen=True)
class HeldView:
    donation: Donation
    match: Match
    address_released: bool
    distance_km: float


def _view(db: Session, org: OrganizationProfile, donation: Donation, match: Match) -> HeldView:
    held = matching.holder(db, donation)
    return HeldView(
        donation=donation,
        match=match,
        address_released=held is not None and held.organization_id == org.id,
        distance_km=disclosed_distance(org, donation),
    )


def list_accepted(db: Session, user: User) -> list[HeldView]:
    """Donations whose most recent acceptance is this organisation's."""
    org = organizations.get_for_user(db, user)
    views = []
    for match in db.scalars(
        select(Match)
        .where(Match.organization_id == org.id, Match.response == OfferResponse.ACCEPTED)
        .order_by(Match.responded_at.desc())
    ):
        current = matching.current_acceptance(db, match.donation_id)
        if current is not None and current.id == match.id:
            views.append(_view(db, org, db.get(Donation, match.donation_id), match))
    return views


def _own_acceptance(db: Session, org: OrganizationProfile, donation_id: uuid.UUID, lock: bool):
    donation = transitions.lock_donation(db, donation_id) if lock else db.get(Donation, donation_id)
    if donation is None:
        raise NotFound("Donation not found.")
    current = matching.current_acceptance(db, donation.id)
    if current is None or current.organization_id != org.id:
        raise NotFound("Donation not found.")
    return donation, current


def get_accepted(db: Session, user: User, donation_id: uuid.UUID) -> HeldView:
    org = organizations.get_for_user(db, user)
    donation, match = _own_acceptance(db, org, donation_id, lock=False)
    return _view(db, org, donation, match)


def schedule_pickup(
    db: Session, user: User, donation_id: uuid.UUID, scheduled_for: datetime, now: datetime
) -> HeldView:
    """The acceptor collects, and so sets the time. It only has to be in the future: the
    donor's pickup window is advisory (shown in the offer), not enforced."""
    org = organizations.get_for_user(db, user)
    donation, match = _own_acceptance(db, org, donation_id, lock=True)
    ensure_available(db, donation, A.SCHEDULE_PICKUP, Actor.ACCEPTOR)
    if scheduled_for <= now:
        raise Unprocessable("A pickup time must be in the future.")
    db.add(
        Handover(
            match_id=match.id,
            mode=HandoverMode.ACCEPTOR_PICKUP,
            scheduled_for=scheduled_for,
            arranged_by_id=user.id,
            created_at=now,
        )
    )
    transitions.apply(db, donation, A.SCHEDULE_PICKUP, Actor.ACCEPTOR, now, user=user, match=match)
    db.commit()
    return _view(db, org, donation, match)


def confirm_receipt(db: Session, user: User, donation_id: uuid.UUID, now: datetime) -> HeldView:
    org = organizations.get_for_user(db, user)
    donation, match = _own_acceptance(db, org, donation_id, lock=True)
    transitions.apply(db, donation, A.CONFIRM_RECEIPT, Actor.ACCEPTOR, now, user=user, match=match)
    db.commit()
    return _view(db, org, donation, match)
