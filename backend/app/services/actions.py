"""Donor and admin lifecycle actions.

Each action: lock the donation, check the edge and actor (app.domain.lifecycle), check
the situational guards (app.domain.policy), then apply through services.transitions,
which writes the StatusEvent. A route never compares statuses itself.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.constants import (
    Actor,
    DonationAction,
    DonationStatus,
    EscalationCause,
    HandoverMode,
    OfferResponse,
    OfferSource,
    RankingTrigger,
    RedirectReason,
)
from app.domain import policy
from app.models import Donation, Handover, User
from app.services import logistics, matching, recycling, transitions
from app.services.errors import Conflict, NotFound, Unprocessable

S = DonationStatus
A = DonationAction


# --- Guards and the actions a viewer may take ----------------------------------------------


def guard_context(db: Session, donation: Donation) -> policy.GuardContext:
    """Compute only what the donation's current state needs."""
    slate_empty = recycler_available = pickup_capable = logistics_available = None
    donor_chose_acceptor_pickup = None
    if donation.status in (S.ESCALATED, S.NEEDS_ADMIN):
        slate_empty = matching.compute_slate(db, donation)[0].is_empty
    if donation.status == S.NEEDS_ADMIN:
        recycler_available = recycling.find_recycler(db, donation) is not None
    if donation.status == S.ACCEPTED:
        held = matching.holder(db, donation)
        pickup_capable = held.organization.pickup_capable if held is not None else None
        logistics_available = bool(logistics.active_providers(db))
        donor_chose_acceptor_pickup = held is not None and matching.acceptor_pickup_chosen(db, held.id)
    return policy.GuardContext(
        is_priority=donation.is_priority,
        slate_empty=slate_empty,
        recycler_available=recycler_available,
        pickup_capable=pickup_capable,
        logistics_available=logistics_available,
        donor_chose_acceptor_pickup=donor_chose_acceptor_pickup,
    )


def available(db: Session, donation: Donation, actor: Actor) -> frozenset[DonationAction]:
    return policy.available_actions(donation.status, actor, guard_context(db, donation))


def handover_options(db: Session, donation: Donation) -> tuple[policy.HandoverOption, ...]:
    """The donor's chosen-but-not-yet-scheduled path. Empty before any choice (the
    donor's own allowed_actions are the three choices then) and empty again once a
    path is actually scheduled (the handover record shows it)."""
    held = matching.holder(db, donation)
    if held is None:
        return ()
    return policy.handover_options(donation.status, matching.acceptor_pickup_chosen(db, held.id))


def ensure_available(db: Session, donation: Donation, action: DonationAction, actor: Actor) -> None:
    transitions.ensure_edge(donation, action, actor)
    blocked = policy.blocked_reason(donation.status, action, guard_context(db, donation))
    if blocked:
        raise Conflict(blocked)


def escalation_cause(db: Session, donation: Donation) -> EscalationCause | None:
    if donation.status != S.ESCALATED:
        return None
    return matching.latest_escalation_cause(db, donation.id)


# --- Donor ------------------------------------------------------------------------------------


def _lock_owned(db: Session, donation_id: uuid.UUID, donor: User) -> Donation:
    donation = transitions.lock_donation(db, donation_id)
    if donation.donor_id != donor.id:
        raise NotFound("Donation not found.")
    return donation


def offer(
    db: Session, donation_id: uuid.UUID, donor: User, organization_id: uuid.UUID | None, now: datetime
) -> Donation:
    """The donor's first offer: the top candidate by default, or any eligible one. The
    slate is re-ranked now and stored with the offer, so the record shows what the
    donor actually chose from. An empty slate escalates at once."""
    donation = _lock_owned(db, donation_id, donor)
    transitions.ensure_edge(donation, A.OFFER, Actor.DONOR)
    slate, n = matching.compute_slate(db, donation)
    if slate.is_empty:
        matching.store_run(db, donation, slate, n, RankingTrigger.DONOR_OFFER, now)
        transitions.apply(db, donation, A.ESCALATE, Actor.SYSTEM, now, cause=EscalationCause.NO_CANDIDATES)
    else:
        candidate = slate.find(organization_id) if organization_id else slate.top()
        if candidate is None:
            raise Conflict("That organisation is not in this donation's eligible slate.")
        run = matching.store_run(db, donation, slate, n, RankingTrigger.DONOR_OFFER, now)
        match = matching.make_offer(db, donation, run, candidate, OfferSource.DONOR, now)
        transitions.apply(db, donation, A.OFFER, Actor.DONOR, now, user=donor, match=match)
    db.commit()
    return donation


def cancel(db: Session, donation_id: uuid.UUID, donor: User, now: datetime) -> Donation:
    donation = _lock_owned(db, donation_id, donor)
    transitions.ensure_edge(donation, A.CANCEL, Actor.DONOR)
    open_offer = matching.open_offer(db, donation.id)
    if open_offer is not None:
        # Closed, not declined: the acceptor did nothing wrong.
        open_offer.respond(OfferResponse.RETRACTED, now)
    transitions.apply(db, donation, A.CANCEL, Actor.DONOR, now, user=donor, match=open_offer)
    db.commit()
    return donation


def rematch(
    db: Session, donation_id: uuid.UUID, donor: User, now: datetime, upgrade_priority: bool = False
) -> Donation:
    """REMATCH or UPGRADE_PRIORITY from ESCALATED. Only offered while the slate is
    non-empty, so it always ends in a new offer, never straight back in ESCALATED."""
    action = A.UPGRADE_PRIORITY if upgrade_priority else A.REMATCH
    donation = _lock_owned(db, donation_id, donor)
    ensure_available(db, donation, action, Actor.DONOR)
    if upgrade_priority:
        donation.is_priority = True
    transitions.apply(db, donation, action, Actor.DONOR, now, user=donor)
    matching.resolve_re_matching(db, donation, now)
    db.commit()
    return donation


def redirect_to_recycling(db: Session, donation_id: uuid.UUID, donor: User, now: datetime) -> Donation:
    donation = _lock_owned(db, donation_id, donor)
    ensure_available(db, donation, A.REDIRECT_TO_RECYCLING, Actor.DONOR)
    recycling.redirect(db, donation, Actor.DONOR, donor, now, reason=RedirectReason.DONOR_CHOICE)
    db.commit()
    return donation


def choose_acceptor_collection(db: Session, donation_id: uuid.UUID, donor: User, now: datetime) -> Donation:
    """ACCEPTED -> ACCEPTED: records the donor's choice that the organisation collects,
    without scheduling a time. A self-loop, not a new state (see lifecycle.py) — this
    unlocks the organisation's own SCHEDULE_PICKUP, which is where a time gets set."""
    donation = _lock_owned(db, donation_id, donor)
    ensure_available(db, donation, A.CHOOSE_ACCEPTOR_COLLECTION, Actor.DONOR)
    held = matching.holder(db, donation)
    transitions.apply(db, donation, A.CHOOSE_ACCEPTOR_COLLECTION, Actor.DONOR, now, user=donor, match=held)
    db.commit()
    return donation


def choose_dropoff(
    db: Session, donation_id: uuid.UUID, donor: User, scheduled_for: datetime, now: datetime
) -> Donation:
    """The donor delivers, and so sets the time. It only has to be in the future: the
    pickup window is advisory."""
    donation = _lock_owned(db, donation_id, donor)
    ensure_available(db, donation, A.CHOOSE_DROPOFF, Actor.DONOR)
    if scheduled_for <= now:
        raise Unprocessable("A drop-off time must be in the future.")
    held = matching.holder(db, donation)
    db.add(
        Handover(
            match_id=held.id,
            mode=HandoverMode.DONOR_DROPOFF,
            scheduled_for=scheduled_for,
            arranged_by_id=donor.id,
            created_at=now,
        )
    )
    transitions.apply(db, donation, A.CHOOSE_DROPOFF, Actor.DONOR, now, user=donor, match=held)
    db.commit()
    return donation


def mark_handed_over(db: Session, donation_id: uuid.UUID, donor: User, now: datetime) -> Donation:
    donation = _lock_owned(db, donation_id, donor)
    transitions.ensure_edge(donation, A.MARK_HANDED_OVER, Actor.DONOR)
    transitions.apply(
        db, donation, A.MARK_HANDED_OVER, Actor.DONOR, now, user=donor, match=matching.holder(db, donation)
    )
    logistics.mark_picked_up(db, donation, now)
    db.commit()
    return donation


def book_pickup(
    db: Session,
    donation_id: uuid.UUID,
    donor: User,
    provider_id: uuid.UUID,
    scheduled_for: datetime,
    wallet_amount: Decimal,
    now: datetime,
) -> Donation:
    """ACCEPTED -> PICKUP_SCHEDULED: a simulated courier booking, paid for by the donor
    (wallet credit first, then a simulated checkout for the rest). It only has to be in
    the future: the pickup window is advisory."""
    donation = _lock_owned(db, donation_id, donor)
    ensure_available(db, donation, A.BOOK_PICKUP, Actor.DONOR)
    if scheduled_for <= now:
        raise Unprocessable("A pickup time must be in the future.")
    logistics.book(db, donation, donor, provider_id, scheduled_for, wallet_amount, now)
    db.commit()
    return donation


# --- Admin --------------------------------------------------------------------------------------


def admin_requeue(db: Session, donation_id: uuid.UUID, admin: User, reason: str, now: datetime) -> Donation:
    """Back into matching: re-offered at once (REQUEUE is offered only while the slate
    is non-empty), or escalated to the donor if the decline threshold is still reached."""
    donation = transitions.lock_donation(db, donation_id)
    ensure_available(db, donation, A.REQUEUE, Actor.ADMIN)
    transitions.apply(db, donation, A.REQUEUE, Actor.ADMIN, now, user=admin, reason=reason)
    matching.resolve_re_matching(db, donation, now)
    db.commit()
    return donation


def admin_redirect_to_recycling(
    db: Session, donation_id: uuid.UUID, admin: User, reason: str, now: datetime
) -> Donation:
    donation = transitions.lock_donation(db, donation_id)
    ensure_available(db, donation, A.REDIRECT_TO_RECYCLING, Actor.ADMIN)
    recycling.redirect(db, donation, Actor.ADMIN, admin, now, reason=reason)
    db.commit()
    return donation


def admin_cancel(db: Session, donation_id: uuid.UUID, admin: User, reason: str, now: datetime) -> Donation:
    donation = transitions.lock_donation(db, donation_id)
    transitions.apply(db, donation, A.CANCEL, Actor.ADMIN, now, user=admin, reason=reason)
    db.commit()
    return donation


def admin_confirm_recycled(
    db: Session, donation_id: uuid.UUID, admin: User, reason: str, now: datetime
) -> Donation:
    """SIMULATED: the admin confirms on the recycler's behalf. Writes the settlement."""
    donation = transitions.lock_donation(db, donation_id)
    recycling.confirm(db, donation, admin, reason, now)
    db.commit()
    return donation
