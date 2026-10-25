"""The in-app notification feed: a per-user view derived on each request. Nothing is
stored for it, so there is no notifications table and no server-side read state. Clients
poll it and remember, per item `key`, what has been read.

The feed merges three sources, newest first:

1. Status events (append-only status_events). Who sees which:
   - a donor: every event on their own donations;
   - an acceptor: events about its own offers (offered, expired, retracted, accepted,
     rejected), and every event that moves a donation out of a held state while the
     organisation holds it. That includes a sweeper STALL to the admin queue, which names
     no offer, so the holder is found from the latest ACCEPT before the event;
   - an admin: events that put a donation where an admin must act
     (lifecycle.states_awaiting(ADMIN): the admin queue and recycling to confirm).
2. Organisation registrations (admins only), from organization_profiles.created_at:
   every organisation starts PENDING and needs an admin to verify it.
3. Chat messages from the other party, in threads the user can read (app.domain.chat):
   a donor, every thread on their donations; an organisation, its own thread while its
   acceptance is the donation's latest. Never the message text.
"""

from datetime import datetime

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session, aliased

from app.constants import Actor, DonationAction, NotificationKind, OfferResponse, Role
from app.domain import lifecycle
from app.models import ChatMessage, Donation, Match, OrganizationProfile, StatusEvent, User
from app.schemas.notification import NotificationOut, notification_key
from app.services import organizations

K = NotificationKind


def _event_audience(db: Session, user: User) -> ColumnElement[bool]:
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


def _events(db: Session, user: User, n: int) -> list[NotificationOut]:
    rows = db.execute(
        select(StatusEvent, Donation, OrganizationProfile.name)
        .join(Donation, Donation.id == StatusEvent.donation_id)
        .outerjoin(Match, Match.id == StatusEvent.match_id)
        .outerjoin(OrganizationProfile, OrganizationProfile.id == Match.organization_id)
        .where(_event_audience(db, user))
        .order_by(StatusEvent.id.desc())
        .limit(n)
    )
    return [
        NotificationOut(
            kind=K.DONATION_EVENT,
            key=notification_key(K.DONATION_EVENT, event.id),
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


def _registrations(db: Session, user: User, n: int) -> list[NotificationOut]:
    if user.role != Role.ADMIN:
        return []
    orgs = db.scalars(
        select(OrganizationProfile)
        .order_by(OrganizationProfile.created_at.desc(), OrganizationProfile.id.desc())
        .limit(n)
    )
    return [
        NotificationOut(
            kind=K.ORGANISATION_REGISTERED,
            key=notification_key(K.ORGANISATION_REGISTERED, org.id),
            at=org.created_at,
            organization_id=org.id,
            organization_name=org.name,
            verification_status=org.verification_status,
        )
        for org in orgs
    ]


def _chat_audience(db: Session, user: User) -> ColumnElement[bool] | None:
    """The threads whose messages `user` may read, over Match and Donation (the same rule
    as app.domain.chat's read access)."""
    if user.role == Role.DONOR:
        return Donation.donor_id == user.id
    if user.role == Role.ACCEPTOR:
        org = organizations.get_for_user(db, user)
        latest = aliased(Match)
        latest_acceptance = (
            select(latest.id)
            .where(latest.donation_id == Match.donation_id, latest.response == OfferResponse.ACCEPTED)
            .order_by(latest.responded_at.desc())
            .limit(1)
            .correlate(Match)
            .scalar_subquery()
        )
        return and_(Match.organization_id == org.id, Match.id == latest_acceptance)
    return None  # admins have no access to chats


def _chat_messages(db: Session, user: User, n: int) -> list[NotificationOut]:
    audience = _chat_audience(db, user)
    if audience is None:
        return []
    rows = db.execute(
        select(ChatMessage, Donation, OrganizationProfile.name)
        .join(Match, Match.id == ChatMessage.match_id)
        .join(Donation, Donation.id == Match.donation_id)
        .join(OrganizationProfile, OrganizationProfile.id == Match.organization_id)
        .where(audience, ChatMessage.sender_id != user.id)
        .order_by(ChatMessage.id.desc())
        .limit(n)
    )
    return [
        NotificationOut(
            kind=K.CHAT_MESSAGE,
            key=notification_key(K.CHAT_MESSAGE, message.id),
            at=message.created_at,
            donation_id=donation.id,
            category=donation.category,
            quantity=donation.quantity,
            actor=message.sender,
            organization_name=org_name,
        )
        for message, donation, org_name in rows
    ]


def _order(item: NotificationOut) -> tuple[datetime, int]:
    # Events written in one transaction share a timestamp; within a source, a larger id
    # is newer. Keys are "<KIND>:<id>".
    source_id = item.key.split(":", 1)[1]
    return item.at, int(source_id) if source_id.isdigit() else 0


def feed(db: Session, user: User, limit: int, offset: int) -> list[NotificationOut]:
    """Newest first. Each source contributes at most offset + limit items, which is all
    the merged page can need."""
    n = offset + limit
    items = _events(db, user, n) + _registrations(db, user, n) + _chat_messages(db, user, n)
    items.sort(key=_order, reverse=True)
    return items[offset : offset + limit]
