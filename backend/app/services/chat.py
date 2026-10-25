"""Donor-organisation chat threads, over app.domain.chat's access rule.

A thread is an accepted offer (a Match answered ACCEPTED). The donor reads every thread
on their own donation; the organisation reads its own while its offer is the donation's
latest acceptance. Anyone else gets the same 404 as for a thread that does not exist.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.constants import Actor, NotificationKind, OfferResponse, Role
from app.domain import chat
from app.models import ChatMessage, ChatRead, Donation, Match, User
from app.schemas.chat import ChatMessageOut, ChatSummaryOut, ChatThreadOut
from app.schemas.notification import notification_key
from app.services import matching, organizations, transitions
from app.services.errors import Conflict, NotFound, Unprocessable


@dataclass(frozen=True)
class ThreadView:
    match: Match
    donation: Donation
    access: chat.ThreadAccess


def _is_current(db: Session, donation: Donation, match: Match) -> bool:
    current = matching.current_acceptance(db, donation.id)
    return current is not None and current.id == match.id


def _viewer(db: Session, user: User, donation: Donation, match: Match) -> Actor | None:
    """The side of `match`'s thread that `user` is on, or None."""
    if user.role == Role.DONOR and donation.donor_id == user.id:
        return Actor.DONOR
    if user.role == Role.ACCEPTOR and organizations.get_for_user(db, user).id == match.organization_id:
        return Actor.ACCEPTOR
    return None


def _view(db: Session, user: User, donation: Donation, match: Match) -> ThreadView | None:
    viewer = _viewer(db, user, donation, match)
    if viewer is None:
        return None
    access = chat.access(viewer, donation.status, _is_current(db, donation, match))
    return ThreadView(match, donation, access) if access.can_read else None


def readable(db: Session, user: User, donation: Donation) -> list[ThreadView]:
    """The threads on `donation` that `user` may read, newest acceptance first."""
    if user.role not in (Role.DONOR, Role.ACCEPTOR):
        return []  # admins have no access to chats
    accepted = db.scalars(
        select(Match)
        .where(Match.donation_id == donation.id, Match.response == OfferResponse.ACCEPTED)
        .order_by(Match.responded_at.desc())
    )
    return [v for v in (_view(db, user, donation, m) for m in accepted) if v is not None]


def threads_for_donation(db: Session, user: User, donation_id: uuid.UUID) -> list[ThreadView]:
    """The threads on a donation that `user` may read. A donor gets [] for their own
    donation before any acceptance; a donation that is not theirs, or (for an
    organisation) one with no thread it can read, is a 404."""
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise NotFound("Donation not found.")
    views = readable(db, user, donation)
    if not views and not (user.role == Role.DONOR and donation.donor_id == user.id):
        raise NotFound("Donation not found.")
    return views


def unread_counts(db: Session, reader: User, match_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Per thread: messages from the other party newer than the reader's read pointer."""
    counts: dict[uuid.UUID, int] = {m: 0 for m in match_ids}
    if not match_ids:
        return counts
    rows = db.execute(
        select(ChatMessage.match_id, func.count())
        .outerjoin(ChatRead, and_(ChatRead.match_id == ChatMessage.match_id, ChatRead.user_id == reader.id))
        .where(
            ChatMessage.match_id.in_(match_ids),
            ChatMessage.sender_id != reader.id,
            ChatMessage.id > func.coalesce(ChatRead.last_read_message_id, 0),
        )
        .group_by(ChatMessage.match_id)
    )
    counts.update({match_id: int(n) for match_id, n in rows})
    return counts


def summary(db: Session, user: User, donation: Donation) -> ChatSummaryOut | None:
    """For a donation's donor or accepting organisation; None if they can read no thread."""
    views = readable(db, user, donation)
    if not views:
        return None
    unread = unread_counts(db, user, [v.match.id for v in views])
    return ChatSummaryOut(
        threads=len(views),
        unread=sum(unread.values()),
        can_write=any(v.access.can_write for v in views),
    )


def _readable_thread(db: Session, user: User, thread_id: uuid.UUID, lock: bool) -> ThreadView:
    match = db.get(Match, thread_id)
    if match is None or match.response != OfferResponse.ACCEPTED:
        raise NotFound("Conversation not found.")
    donation = transitions.lock_donation(db, match.donation_id) if lock else db.get(Donation, match.donation_id)
    view = _view(db, user, donation, match)
    if view is None:
        raise NotFound("Conversation not found.")
    return view


def mark_read(db: Session, user: User, thread_id: uuid.UUID, up_to_message_id: int, now: datetime) -> ThreadView:
    """Move the reader's pointer forward to a message they were shown. Allowed on any
    thread they can read, open or closed. Never moves backward, so two tabs cannot undo
    each other."""
    view = _readable_thread(db, user, thread_id, lock=False)
    message = db.get(ChatMessage, up_to_message_id)
    if message is None or message.match_id != view.match.id:
        raise Unprocessable("That message is not in this conversation.")
    db.execute(
        pg_insert(ChatRead)
        .values(match_id=view.match.id, user_id=user.id, last_read_message_id=message.id, updated_at=now)
        .on_conflict_do_update(
            index_elements=[ChatRead.match_id, ChatRead.user_id],
            set_={
                "last_read_message_id": func.greatest(ChatRead.last_read_message_id, message.id),
                "updated_at": now,
            },
        )
    )
    db.commit()
    return view


def messages(db: Session, match_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ChatMessage]]:
    found: dict[uuid.UUID, list[ChatMessage]] = {m: [] for m in match_ids}
    if match_ids:
        for message in db.scalars(
            select(ChatMessage).where(ChatMessage.match_id.in_(match_ids)).order_by(ChatMessage.id)
        ):
            found[message.match_id].append(message)
    return found


def post_message(db: Session, user: User, thread_id: uuid.UUID, body: str, now: datetime) -> ThreadView:
    """Append a message. The donation row is locked, so a post cannot interleave with a
    transition that closes the thread (a stall, say). Your own messages are never unread
    for you, so posting leaves the read pointer alone."""
    view = _readable_thread(db, user, thread_id, lock=True)
    if not view.access.can_write:
        raise Conflict("This conversation is closed: the organisation no longer holds the donation.")
    db.add(
        ChatMessage(
            match_id=view.match.id,
            sender_id=user.id,
            sender=_viewer(db, user, view.donation, view.match),
            body=body,
            created_at=now,
        )
    )
    db.commit()
    return view


# --- Output ---------------------------------------------------------------------------------


def message_out(message: ChatMessage, reader: User, organization_name: str) -> ChatMessageOut:
    mine = message.sender_id == reader.id
    return ChatMessageOut(
        id=message.id,
        at=message.created_at,
        sender=message.sender,
        sender_name=organization_name if message.sender == Actor.ACCEPTOR else None,
        mine=mine,
        body=message.body,
        notification_key=None if mine else notification_key(NotificationKind.CHAT_MESSAGE, message.id),
    )


def threads_out(db: Session, reader: User, views: list[ThreadView]) -> list[ChatThreadOut]:
    by_thread = messages(db, [v.match.id for v in views])
    unread = unread_counts(db, reader, [v.match.id for v in views])
    return [
        ChatThreadOut(
            id=v.match.id,
            donation_id=v.donation.id,
            organization_name=v.match.organization.name,
            accepted_at=v.match.responded_at,
            can_write=v.access.can_write,
            closed_reason=v.access.closed_reason,
            unread=unread[v.match.id],
            messages=[message_out(m, reader, v.match.organization.name) for m in by_thread[v.match.id]],
        )
        for v in views
    ]
