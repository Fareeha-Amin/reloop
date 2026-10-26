"""Lifecycle policy: the pure decisions around the transition table (non-negotiable 11).

- reach and queue priority (the rejection and priority boosts);
- how a RE_MATCHING donation resolves (re-offer or escalate);
- situational guards that hide an edge for one donation (an empty slate, no recycler,
  an organisation that does not collect), so no action is offered that would only loop
  back to where it started;
- the sweeper's rules: which time-based action, if any, is due for a donation.

No database and no clock: callers pass the facts and `now`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from app.constants import (
    ESCALATION_THRESHOLD,
    ESCALATION_TTL,
    HANDOVER_GRACE,
    LISTED_STALL,
    STALL_TIMEOUTS,
    Actor,
    DonationAction,
    DonationStatus,
    EscalationCause,
    OfferResponse,
)
from app.domain import lifecycle
from app.domain.scoring import MatchingConfig

S = DonationStatus
A = DonationAction

# Responses that count as a decline: they widen the radius, raise queue priority and
# count toward escalation. RETRACTED is not the acceptor's doing, so it is not one.
DECLINE_RESPONSES: frozenset[OfferResponse] = frozenset({OfferResponse.REJECTED, OfferResponse.EXPIRED})
# Responses that count in an organisation's acceptance rate.
DECIDED_RESPONSES: frozenset[OfferResponse] = DECLINE_RESPONSES | {OfferResponse.ACCEPTED}


# --- Boosts -------------------------------------------------------------------------------


def rejection_boost(declines: int, config: MatchingConfig) -> float:
    if not config.rejection_boost_enabled:
        return 1.0
    return min(config.rejection_boost_cap, 1.0 + config.rejection_boost_step * declines)


def effective_radius_km(declines: int, config: MatchingConfig) -> float:
    """Reach widens with each decline, capped. Without the boost it never widens."""
    if not config.rejection_boost_enabled:
        return config.max_radius_km
    return min(config.radius_cap_km, config.max_radius_km * (1.0 + config.radius_step * declines))


def queue_priority(is_priority: bool, declines: int, config: MatchingConfig) -> float:
    """Orders an acceptor's inbox of open offers. Never applied to candidate scores."""
    return (config.priority_boost if is_priority else 1.0) * rejection_boost(declines, config)


# --- Resolving RE_MATCHING ---------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    action: DonationAction
    cause: EscalationCause | None = None


def rematch_decision(
    *,
    declines_since_escalation: int,
    slate_empty: bool,
    threshold: int = ESCALATION_THRESHOLD,
) -> Decision:
    """RE_MATCHING always resolves in the same transaction: re-offer to the top
    candidate, or hand the decision back to the donor."""
    if declines_since_escalation >= threshold:
        return Decision(A.ESCALATE, EscalationCause.THRESHOLD_REACHED)
    if slate_empty:
        return Decision(A.ESCALATE, EscalationCause.NO_CANDIDATES)
    return Decision(A.REOFFER)


# --- Situational guards ---------------------------------------------------------------------


@dataclass(frozen=True)
class GuardContext:
    """Facts about one donation that can hide an edge. None means "not computed"; the
    caller computes whatever the donation's current state needs."""

    is_priority: bool = False
    slate_empty: bool | None = None
    recycler_available: bool | None = None
    pickup_capable: bool | None = None  # of the organisation holding the donation
    logistics_available: bool | None = None  # any active LogisticsProvider


def blocked_reason(state: DonationStatus, action: DonationAction, ctx: GuardContext) -> str | None:
    """Why this edge is unavailable for this donation right now, or None."""
    if (state, action) in {(S.ESCALATED, A.REMATCH), (S.ESCALATED, A.UPGRADE_PRIORITY), (S.NEEDS_ADMIN, A.REQUEUE)}:
        if ctx.slate_empty:
            return "No eligible organisation remains for this donation; re-matching would escalate it straight back."
    if (state, action) == (S.ESCALATED, A.UPGRADE_PRIORITY) and ctx.is_priority:
        return "This donation is already a priority donation."
    if (state, action) == (S.NEEDS_ADMIN, A.REDIRECT_TO_RECYCLING) and ctx.recycler_available is False:
        return "No active recycler accepts this category within range; redirecting would return it to this queue."
    if (state, action) == (S.ACCEPTED, A.SCHEDULE_PICKUP) and ctx.pickup_capable is False:
        return "This organisation does not collect; the donor must choose drop-off."
    if (state, action) == (S.ACCEPTED, A.BOOK_PICKUP) and ctx.logistics_available is False:
        return "No active logistics provider is available to book a platform pickup."
    return None


def available_actions(state: DonationStatus, actor: Actor, ctx: GuardContext) -> frozenset[DonationAction]:
    return frozenset(
        action
        for action in lifecycle.allowed_actions(state, actor)
        if blocked_reason(state, action, ctx) is None
    )


# --- The sweeper ------------------------------------------------------------------------------

# The time-based actions the sweeper may take in each state. Tests check that every
# state waiting on a person appears here (or has an admin exit), and that each entry is
# a SYSTEM edge of the transition table.
SWEEP_RULES: Mapping[DonationStatus, frozenset[DonationAction]] = MappingProxyType(
    {
        S.LISTED: frozenset({A.ESCALATE}),
        S.MATCHED: frozenset({A.EXPIRE}),
        S.ESCALATED: frozenset({A.STALL}),
        S.ACCEPTED: frozenset({A.STALL}),
        S.PICKUP_SCHEDULED: frozenset({A.STALL}),
        S.IN_TRANSIT: frozenset({A.STALL}),
        S.WASTE_REDIRECTED: frozenset({A.STALL}),
    }
)


@dataclass(frozen=True)
class SweepFacts:
    """The donor's pickup window is advisory and deliberately not among these facts."""

    status: DonationStatus
    entered_at: datetime  # when the donation entered its current status (creation, for LISTED)
    offer_expires_at: datetime | None = None  # the open offer, when MATCHED
    handover_at: datetime | None = None  # the agreed time, when PICKUP_SCHEDULED


def _deadline(facts: SweepFacts) -> tuple[datetime, Decision] | None:
    """The one deadline a donation in this state is waiting on, and what happens then."""
    match facts.status:
        case S.LISTED:
            return facts.entered_at + LISTED_STALL, Decision(A.ESCALATE, EscalationCause.NOT_OFFERED)
        case S.MATCHED if facts.offer_expires_at is not None:
            return facts.offer_expires_at, Decision(A.EXPIRE)
        case S.PICKUP_SCHEDULED:
            base = facts.handover_at if facts.handover_at is not None else facts.entered_at
            return base + HANDOVER_GRACE, Decision(A.STALL)
        case S.ESCALATED:
            return facts.entered_at + ESCALATION_TTL, Decision(A.STALL)
        case S.ACCEPTED | S.IN_TRANSIT | S.WASTE_REDIRECTED:
            return facts.entered_at + STALL_TIMEOUTS[facts.status], Decision(A.STALL)
    return None


def sweep_decision(facts: SweepFacts, now: datetime) -> Decision | None:
    """The time-based action due for a donation, or None."""
    deadline = _deadline(facts)
    if deadline is None or now < deadline[0]:
        return None
    return deadline[1]
