import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from app.constants import Actor, DonationAction, DonationStatus
from app.schemas.matching import RejectIn, ScheduleIn
from app.schemas.offer import AcceptedDonationOut, OfferOut
from app.security.deps import AcceptorUser, DbSession
from app.services import actions, chat, offers, organizations

router = APIRouter(prefix="/organisations/me", tags=["acceptor: offers & accepted donations"])


def _now() -> datetime:
    return datetime.now(UTC)


def _accepted_out(db, view, user) -> AcceptedDonationOut:
    allowed = actions.available(db, view.donation, Actor.ACCEPTOR) if view.address_released else frozenset()
    # True only when this organisation collects and the donor hasn't yet chosen that
    # path (otherwise SCHEDULE_PICKUP is either moot or already in `allowed`).
    org = organizations.get_for_user(db, user)
    awaiting = (
        view.donation.status == DonationStatus.ACCEPTED
        and org.pickup_capable
        and DonationAction.SCHEDULE_PICKUP not in allowed
    )
    return AcceptedDonationOut.build(view, allowed, chat.summary(db, user, view.donation), awaiting)


@router.get("/offers", response_model=list[OfferOut])
def list_offers(user: AcceptorUser, db: DbSession):
    """Open offers, highest queue priority first (priority donations and donations that
    have been declined elsewhere rise), then oldest first. No address or coordinates."""
    return [OfferOut.build(v) for v in offers.inbox(db, user, _now())]


@router.get("/offers/{match_id}", response_model=OfferOut)
def get_offer(match_id: uuid.UUID, user: AcceptorUser, db: DbSession):
    return OfferOut.build(offers.get_offer(db, user, match_id))


@router.post("/offers/{match_id}/accept", response_model=AcceptedDonationOut)
def accept_offer(match_id: uuid.UUID, user: AcceptorUser, db: DbSession):
    """MATCHED → ACCEPTED. Releases the precise pickup address to this organisation (the
    release is recorded) for as long as it holds the donation."""
    donation = offers.accept(db, user, match_id, _now())
    return _accepted_out(db, offers.get_accepted(db, user, donation.id), user)


@router.post("/offers/{match_id}/reject", response_model=OfferOut)
def reject_offer(match_id: uuid.UUID, data: RejectIn, user: AcceptorUser, db: DbSession):
    """Recorded with its reason code, never deleted. This organisation is never offered
    the donation again; it is re-offered or escalated to its donor at once."""
    offers.reject(db, user, match_id, data.reason_code, data.note, _now())
    return OfferOut.build(offers.get_offer(db, user, match_id))


@router.get("/donations", response_model=list[AcceptedDonationOut])
def list_accepted_donations(user: AcceptorUser, db: DbSession):
    return [_accepted_out(db, v, user) for v in offers.list_accepted(db, user)]


@router.get("/donations/{donation_id}", response_model=AcceptedDonationOut)
def get_accepted_donation(donation_id: uuid.UUID, user: AcceptorUser, db: DbSession):
    return _accepted_out(db, offers.get_accepted(db, user, donation_id), user)


@router.post("/donations/{donation_id}/schedule-pickup", response_model=AcceptedDonationOut)
def schedule_pickup(donation_id: uuid.UUID, data: ScheduleIn, user: AcceptorUser, db: DbSession):
    """ACCEPTED → PICKUP_SCHEDULED, this organisation collecting. The time must be in the
    future; the donor's pickup window is advisory. Not offered if the organisation does
    not collect (pickup_capable false)."""
    return _accepted_out(db, offers.schedule_pickup(db, user, donation_id, data.scheduled_for, _now()), user)


@router.post("/donations/{donation_id}/confirm-receipt", response_model=AcceptedDonationOut)
def confirm_receipt(donation_id: uuid.UUID, user: AcceptorUser, db: DbSession):
    """PICKUP_SCHEDULED or IN_TRANSIT → COMPLETED: reuse, an outcome."""
    return _accepted_out(db, offers.confirm_receipt(db, user, donation_id, _now()), user)
