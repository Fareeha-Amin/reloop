"""Platform-arranged pickup against the database: quoting, booking, and the side
effects that keep a Booking's own progress and refund in step with the donation.

SIMULATED: no real courier, no real payment gateway. `book` does the donor's checkout
(auto-succeeds) in the same transaction as the booking and its wallet debit, same
pattern as app.services.recycling. `cancel_and_refund` is the other half of that
contract: whatever a booking paid for it must receive back if the courier never
delivers (see app.services.sweeper, the only path out of lifecycle.BOOKED_STATES that
does not complete).

The same Booking/Payment machinery also serves a platform pickup to a recycler
(`book_recycler_pickup`): the destination is the assigned WasteCollector's address
instead of an accepting organisation's, and the Handover it creates carries
recycling_id instead of match_id (app.models.matching.Handover)."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Actor, CommissionSource, DonationAction, HandoverMode, WalletTxnType
from app.domain import logistics as rules
from app.domain.geo import haversine_km
from app.models import Booking, Donation, Handover, LogisticsProvider, Payment, Recycling, User
from app.services import commission, matching, recycling, transitions, wallet
from app.services.errors import Conflict


def active_providers(db: Session) -> list[LogisticsProvider]:
    return list(db.scalars(select(LogisticsProvider).where(LogisticsProvider.is_active.is_(True))))


def _simulated_id(prefix: str) -> str:
    return f"SIM-{prefix}-{secrets.token_hex(6).upper()}"


@dataclass(frozen=True)
class ProviderQuote:
    provider: LogisticsProvider
    cost: Decimal


@dataclass(frozen=True)
class PickupQuote:
    distance_km: float
    wallet_balance: Decimal
    quotes: list[ProviderQuote]


def _distance_to_holder(db: Session, donation: Donation):
    held = matching.holder(db, donation)
    if held is None:
        raise Conflict("This donation is not currently held by an organisation.")
    distance = haversine_km(
        donation.pickup_latitude, donation.pickup_longitude, held.organization.latitude, held.organization.longitude
    )
    return held, distance


def _distance_to_recycler(db: Session, donation: Donation) -> tuple[Recycling, float]:
    assignment = recycling.current(db, donation.id)
    if assignment is None:
        raise Conflict("This donation has no open recycling assignment.")
    distance = haversine_km(
        donation.pickup_latitude, donation.pickup_longitude, assignment.collector.latitude, assignment.collector.longitude
    )
    return assignment, distance


def quote(db: Session, donation: Donation, donor_id: uuid.UUID) -> PickupQuote:
    """A preview: nothing is stored. Booking re-quotes and stores what it quoted."""
    _, distance = _distance_to_holder(db, donation)
    quotes = [
        ProviderQuote(p, rules.quote_cost(distance, p.base_fee, p.per_km_rate)) for p in active_providers(db)
    ]
    return PickupQuote(distance_km=round(distance, 3), wallet_balance=wallet.balance(db, donor_id), quotes=quotes)


def quote_recycler_pickup(db: Session, donation: Donation, donor_id: uuid.UUID) -> PickupQuote:
    """A preview of a platform pickup to the assigned recycler. A preview: nothing is
    stored. book_recycler_pickup re-quotes and stores what it quoted."""
    _, distance = _distance_to_recycler(db, donation)
    quotes = [
        ProviderQuote(p, rules.quote_cost(distance, p.base_fee, p.per_km_rate)) for p in active_providers(db)
    ]
    return PickupQuote(distance_km=round(distance, 3), wallet_balance=wallet.balance(db, donor_id), quotes=quotes)


def book(
    db: Session,
    donation: Donation,
    donor: User,
    provider_id: uuid.UUID,
    scheduled_for: datetime,
    wallet_amount: Decimal,
    now: datetime,
) -> Booking:
    """ACCEPTED -> PICKUP_SCHEDULED. The donor's wallet balance covers as much of the
    cost as they ask for (and can afford); the rest is a simulated, auto-succeeding
    checkout. The wallet is optional: wallet_amount of 0 pays the full cost by gateway."""
    held, distance = _distance_to_holder(db, donation)
    provider = db.get(LogisticsProvider, provider_id)
    if provider is None or not provider.is_active:
        raise Conflict("That logistics provider is not available.")

    cost = rules.quote_cost(distance, provider.base_fee, provider.per_km_rate)
    available_balance = wallet.balance(db, donor.id)
    wallet_applied, gateway_amount = rules.wallet_split(cost, wallet_amount, available_balance)

    handover = Handover(
        match_id=held.id, mode=HandoverMode.PLATFORM_PICKUP, scheduled_for=scheduled_for,
        arranged_by_id=donor.id, created_at=now,
    )
    db.add(handover)
    db.flush()

    booking = Booking(
        donation_id=donation.id, handover_id=handover.id, provider_id=provider.id,
        distance_km=round(distance, 3), cost=cost, wallet_applied=wallet_applied,
        gateway_amount=gateway_amount, arranged_by_id=donor.id, booked_at=now,
    )
    db.add(booking)
    db.flush()

    db.add(
        Payment(
            booking_id=booking.id, donor_id=donor.id, amount=gateway_amount,
            transaction_id=_simulated_id("PAY"), paid_at=now,
        )
    )
    if wallet_applied > 0:
        wallet.record(
            db, donor.id, WalletTxnType.PICKUP_DEBIT, -wallet_applied, now,
            reference_booking_id=booking.id, note="Platform pickup booked.",
        )
    commission.record(db, CommissionSource.LOGISTICS, booking.id, rules.commission_amount(cost), now)

    transitions.apply(db, donation, DonationAction.BOOK_PICKUP, Actor.DONOR, now, user=donor, match=held)
    return booking


def book_recycler_pickup(
    db: Session,
    donation: Donation,
    donor: User,
    provider_id: uuid.UUID,
    scheduled_for: datetime,
    wallet_amount: Decimal,
    now: datetime,
) -> Booking:
    """WASTE_REDIRECTED -> RECYCLING_IN_TRANSIT. Same simulated checkout as `book`, to
    the assigned recycler's address instead of an accepting organisation's. The donor
    pays the quote in full by default; the wallet is optional, same as a donation
    pickup (it is clamped and never raises on a zero balance)."""
    assignment, distance = _distance_to_recycler(db, donation)
    provider = db.get(LogisticsProvider, provider_id)
    if provider is None or not provider.is_active:
        raise Conflict("That logistics provider is not available.")

    cost = rules.quote_cost(distance, provider.base_fee, provider.per_km_rate)
    available_balance = wallet.balance(db, donor.id)
    wallet_applied, gateway_amount = rules.wallet_split(cost, wallet_amount, available_balance)

    handover = Handover(
        recycling_id=assignment.id, mode=HandoverMode.PLATFORM_PICKUP, scheduled_for=scheduled_for,
        arranged_by_id=donor.id, created_at=now,
    )
    db.add(handover)
    db.flush()

    booking = Booking(
        donation_id=donation.id, handover_id=handover.id, provider_id=provider.id,
        distance_km=round(distance, 3), cost=cost, wallet_applied=wallet_applied,
        gateway_amount=gateway_amount, arranged_by_id=donor.id, booked_at=now,
    )
    db.add(booking)
    db.flush()

    db.add(
        Payment(
            booking_id=booking.id, donor_id=donor.id, amount=gateway_amount,
            transaction_id=_simulated_id("PAY"), paid_at=now,
        )
    )
    if wallet_applied > 0:
        wallet.record(
            db, donor.id, WalletTxnType.PICKUP_DEBIT, -wallet_applied, now,
            reference_booking_id=booking.id, note="Platform pickup to recycler booked.",
        )
    commission.record(db, CommissionSource.LOGISTICS, booking.id, rules.commission_amount(cost), now)

    transitions.apply(db, donation, DonationAction.BOOK_RECYCLER_PICKUP, Actor.DONOR, now, user=donor)
    return booking


def _booking_for_current_acceptance(db: Session, donation: Donation) -> Booking | None:
    """The booking tied to the donation's current (or most recent) accepted offer,
    whatever the donation's status is right now — unlike matching.holder, not gated by
    lifecycle.HELD_STATES, so this still finds it the moment a STALL has just left them."""
    match = matching.current_acceptance(db, donation.id)
    if match is None or match.handover is None or match.handover.mode != HandoverMode.PLATFORM_PICKUP:
        return None
    return db.scalar(select(Booking).where(Booking.handover_id == match.handover.id))


def _booking_for_current_recycling(db: Session, donation: Donation) -> Booking | None:
    """The booking tied to the donation's current (or most recent) recycling
    assignment, whatever the donation's status is right now — same reasoning as
    `_booking_for_current_acceptance`, so a STALL still finds it the moment it fires."""
    assignment = recycling.current(db, donation.id)
    if assignment is None or assignment.handover is None or assignment.handover.mode != HandoverMode.PLATFORM_PICKUP:
        return None
    return db.scalar(select(Booking).where(Booking.handover_id == assignment.handover.id))


def mark_picked_up(db: Session, donation: Donation, now: datetime) -> None:
    """The donor has handed the goods to the courier (MARK_HANDED_OVER)."""
    booking = _booking_for_current_acceptance(db, donation)
    if booking is not None and booking.picked_up_at is None and booking.cancelled_at is None and booking.delivered_at is None:
        booking.picked_up_at = now


def mark_delivered(db: Session, donation: Donation, now: datetime) -> None:
    """The acceptor has confirmed receipt (CONFIRM_RECEIPT), whether or not the donor
    ever clicked "handed over" first."""
    booking = _booking_for_current_acceptance(db, donation)
    if booking is not None and booking.delivered_at is None and booking.cancelled_at is None:
        booking.delivered_at = now


def mark_recycler_delivered(db: Session, donation: Donation, now: datetime) -> None:
    """The admin's CONFIRM_RECYCLED stands in for the recycler's own receipt (there is
    no recycler login): it is the moment a platform-pickup booking to a recycler counts
    as delivered, whether or not it had any earlier progress recorded."""
    booking = _booking_for_current_recycling(db, donation)
    if booking is not None and booking.delivered_at is None and booking.cancelled_at is None:
        booking.delivered_at = now


def _open_booking(db: Session, donation: Donation) -> Booking | None:
    """The one booking (to an organisation or to a recycler) that is paid for but not
    yet delivered or cancelled, if any. At most one of the two lookups can find an open
    booking at a time: the other leg, if it exists, was already closed before this one
    began (its own STALL already cancelled and refunded it)."""
    for booking in (_booking_for_current_acceptance(db, donation), _booking_for_current_recycling(db, donation)):
        if booking is not None and booking.delivered_at is None and booking.cancelled_at is None:
            return booking
    return None


def cancel_and_refund(db: Session, donation: Donation, now: datetime, reason: str) -> None:
    """The one hook for "nothing may be left paid but undelivered without a refund
    record": called wherever a donation leaves lifecycle.BOOKED_STATES without
    completing (today, only the sweeper's STALL). Cancels the open booking, refunds its
    payment in full, credits back any wallet amount spent, and reverses its commission
    with a second, negated ledger row. A no-op if there is no open platform-pickup
    booking, to an organisation or to a recycler."""
    booking = _open_booking(db, donation)
    if booking is None:
        return
    booking.cancelled_at = now
    booking.cancel_reason = reason
    payment = booking.payment
    if payment is not None and payment.refunded_at is None:
        payment.refunded_at = now
        payment.refund_transaction_id = _simulated_id("RFD")
    if booking.wallet_applied > 0:
        wallet.record(
            db, booking.arranged_by_id, WalletTxnType.PICKUP_REFUND, booking.wallet_applied, now,
            reference_booking_id=booking.id, note="Platform pickup cancelled before delivery.",
        )
    commission.record(
        db, CommissionSource.LOGISTICS, booking.id, -rules.commission_amount(booking.cost), now,
        note="Reversal: booking cancelled before delivery.",
    )
