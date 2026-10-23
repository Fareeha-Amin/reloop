"""The one place a donation's status changes (non-negotiables 2 and 9).

`apply` checks the move against app.domain.lifecycle (edge and actor), requires a reason
where the table says so, writes the StatusEvent and sets the status, all in the caller's
transaction. Callers must hold the donation row lock (`lock_donation`), so concurrent
requests and the sweeper serialise on the donation.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.constants import Actor, DonationAction, EscalationCause
from app.domain import lifecycle
from app.models import Donation, Match, StatusEvent, User
from app.services.errors import Conflict, NotFound, Unprocessable


def lock_donation(db: Session, donation_id: uuid.UUID) -> Donation:
    """SELECT ... FOR UPDATE, refreshing any copy already in the session."""
    donation = db.get(Donation, donation_id, with_for_update=True, populate_existing=True)
    if donation is None:
        raise NotFound("Donation not found.")
    return donation


def ensure_edge(donation: Donation, action: DonationAction, actor: Actor) -> None:
    """Raise Conflict unless `actor` may perform `action` from the donation's state."""
    try:
        lifecycle.check_actor(donation.status, action, actor)
    except (lifecycle.InvalidTransition, lifecycle.ActorNotAllowed) as exc:
        raise Conflict(str(exc)) from exc


def apply(
    db: Session,
    donation: Donation,
    action: DonationAction,
    actor: Actor,
    now: datetime,
    *,
    user: User | None = None,
    match: Match | None = None,
    cause: EscalationCause | None = None,
    reason: str | None = None,
) -> StatusEvent:
    ensure_edge(donation, action, actor)
    if lifecycle.requires_reason(donation.status, action) and not (reason and reason.strip()):
        raise Unprocessable(f"{action.value} requires a recorded reason.")
    target = lifecycle.next_state(donation.status, action)
    event = StatusEvent(
        donation_id=donation.id,
        from_state=donation.status,
        to_state=target,
        action=action,
        actor=actor,
        actor_id=user.id if user is not None else None,
        match=match,
        cause=cause,
        reason=reason.strip() if reason else None,
        created_at=now,
    )
    db.add(event)
    donation.status = target
    return event
