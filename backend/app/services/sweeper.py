"""The deadline sweeper: `sweep(db, now)`, a plain function. It runs in-process every
SWEEP_INTERVAL (`run_periodically`, started by the app lifespan unless SWEEPER_ENABLED
is false), and on demand from POST /admin/sweep or `python -m app.cli sweep`.
No Celery, no Redis.

The decisions are made by the pure app.domain.policy.sweep_decision; this module only
gathers the facts and applies the result. Each donation is handled in its own
transaction under its row lock (SKIP LOCKED, so a donation being changed by a request,
or by another process's sweep, is left for the next run), and the decision is re-made
under the lock. Running it twice in a row does nothing the second time.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import Actor, DonationAction, DonationStatus, OfferResponse
from app.db import get_engine
from app.domain import lifecycle, policy
from app.models import Donation, StatusEvent
from app.services import logistics, matching, transitions

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SweepItem:
    donation_id: uuid.UUID
    from_state: DonationStatus
    action: DonationAction
    to_state: DonationStatus


@dataclass
class SweepReport:
    now: datetime
    examined: int = 0
    skipped_locked: int = 0
    applied: list[SweepItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def entered_at(db: Session, donation: Donation) -> datetime:
    """When the donation entered its current status (creation, for LISTED)."""
    at = db.scalar(
        select(func.max(StatusEvent.created_at)).where(
            StatusEvent.donation_id == donation.id, StatusEvent.to_state == donation.status
        )
    )
    return at or donation.created_at


def facts(db: Session, donation: Donation) -> policy.SweepFacts:
    offer = matching.open_offer(db, donation.id) if donation.status == DonationStatus.MATCHED else None
    held = matching.holder(db, donation)
    handover = held.handover if held is not None else None
    return policy.SweepFacts(
        status=donation.status,
        entered_at=entered_at(db, donation),
        offer_expires_at=offer.expires_at if offer else None,
        handover_at=handover.scheduled_for if handover else None,
    )


def apply_due(db: Session, donation: Donation, now: datetime) -> SweepItem | None:
    """Apply the time-based action due for a locked donation, if any. Also used when an
    acceptor answers an offer that is already past its deadline."""
    decision = policy.sweep_decision(facts(db, donation), now)
    if decision is None:
        return None
    before = donation.status
    action = decision.action
    if action == DonationAction.EXPIRE:
        offer = matching.open_offer(db, donation.id)
        offer.respond(OfferResponse.EXPIRED, now)
        transitions.apply(db, donation, action, Actor.SYSTEM, now, match=offer)
        matching.resolve_re_matching(db, donation, now)
    else:
        transitions.apply(db, donation, action, Actor.SYSTEM, now, cause=decision.cause)
    if action == DonationAction.STALL and before in lifecycle.HELD_STATES:
        # The only path out of HELD_STATES that does not complete: a platform-pickup
        # booking paid for but not yet delivered must be cancelled and refunded now,
        # whatever the admin does with the donation next (tests/unit/test_lifecycle.py
        # asserts, from the table, that STALL is the only such exit).
        logistics.cancel_and_refund(db, donation, now, reason="Handover stalled; donation sent to the admin queue.")
    return SweepItem(donation.id, before, action, donation.status)


def sweep(db: Session, now: datetime) -> SweepReport:
    report = SweepReport(now=now)
    ids = list(
        db.scalars(
            select(Donation.id)
            .where(Donation.status.in_(list(policy.SWEEP_RULES)))
            .order_by(Donation.created_at)
        )
    )
    db.commit()  # end the read transaction; each donation gets its own
    for donation_id in ids:
        try:
            donation = db.scalar(
                select(Donation)
                .where(Donation.id == donation_id)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if donation is None:
                report.skipped_locked += 1
                db.rollback()
                continue
            report.examined += 1
            item = apply_due(db, donation, now)
            db.commit()
            if item is not None:
                report.applied.append(item)
        except Exception as exc:  # one bad donation must not stop the sweep, nor vanish
            db.rollback()
            logger.exception("Sweep failed for donation %s", donation_id)
            report.errors.append(f"{donation_id}: {exc}")
    return report


# --- In-process schedule --------------------------------------------------------------------


def sweep_now() -> SweepReport:
    """One sweep against the application database, with the real clock."""
    with Session(get_engine()) as db:
        report = sweep(db, datetime.now(UTC))
    if report.applied or report.errors:
        logger.info(
            "Sweep applied %d action(s), %d error(s)", len(report.applied), len(report.errors)
        )
    return report


async def run_periodically(
    interval_seconds: float, run_once: Callable[[], object], stop: asyncio.Event
) -> None:
    """Run `run_once` now and then every `interval_seconds` until `stop` is set. The
    sweep is synchronous, so it runs in a worker thread and never blocks requests. A
    failed run is logged and the loop carries on: the next run retries."""
    while not stop.is_set():
        try:
            await asyncio.to_thread(run_once)
        except Exception:
            logger.exception("Background sweep failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
