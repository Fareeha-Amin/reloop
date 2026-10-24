"""The in-app notification feed: a per-user view over the append-only status_events log.
Nothing is stored for it, so there is no notifications table. Clients poll it, and keep
the id of the newest event they have shown to count unread ones.

Who sees which events:
- a donor: every event on their own donations;
- an acceptor: events about its own offers (offered, expired, retracted, accepted,
  rejected), and every event that moves a donation out of a held state while the
  organisation holds it. That includes a sweeper STALL to the admin queue, which names
  no offer, so the holder is found from the latest ACCEPT before the event;
- an admin: events that put a donation where an admin must act
  (lifecycle.states_awaiting(ADMIN): the admin queue and recycling to confirm).
"""

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import Actor, DonationAction, Role
from app.domain import lifecycle
from app.models import Donation, Match, OrganizationProfile, StatusEvent, User
from app.schemas.notification import NotificationOut
from app.services import organizations


def _audience(db: Session, user: User) -> ColumnElement[bool]:
    """The events `user` is party to, as a WHERE clause over StatusEvent and Donation."""
    if user.role == Role.DONOR:
        return Donation.donor_id == user.id
    if user.role == Role.ADMIN:
        return StatusEvent.to_state.in_(lifecycle.states_awaiting(Actor.ADMIN))

    org = organizations.get_for_user(db, user)
    own = aliased(Match)
    own_offers = select(own.id).where(own.organization_id == org.id)
    accept_event, accepted = aliased(StatusEvent), aliased(Match)
    holder_at_event = (
        select(accepted.organization_id)
        .select_from(accept_event)
        .join(accepted, accepted.id == accept_event.match_id)
        .where(
            accept_event.donation_id == StatusEvent.donation_id,
            accept_event.action == DonationAction.ACCEPT,
            accept_event.id < StatusEvent.id,
        )
        .order_by(accept_event.id.desc())
        .limit(1)
        .correlate(StatusEvent)
        .scalar_subquery()
    )
    return or_(
        StatusEvent.match_id.in_(own_offers),
        and_(StatusEvent.from_state.in_(lifecycle.HELD_STATES), holder_at_event == org.id),
    )


def feed(db: Session, user: User, limit: int, offset: int) -> list[NotificationOut]:
    """Newest first."""
    rows = db.execute(
        select(StatusEvent, Donation, OrganizationProfile.name)
        .join(Donation, Donation.id == StatusEvent.donation_id)
        .outerjoin(Match, Match.id == StatusEvent.match_id)
        .outerjoin(OrganizationProfile, OrganizationProfile.id == Match.organization_id)
        .where(_audience(db, user))
        .order_by(StatusEvent.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        NotificationOut(
            id=event.id,
            at=event.created_at,
            donation_id=donation.id,
            category=donation.category,
            quantity=donation.quantity,
            action=event.action,
            actor=event.actor,
            from_state=event.from_state,
            to_state=event.to_state,
            cause=event.cause,
            organization_name=org_name,
        )
        for event, donation, org_name in rows
    ]
