"""Donation lifecycle — the explicit transition table (non-negotiables 1, 2 and 11).

This module is the only place that decides which status may follow which, and who may
cause it. Route handlers and services ask it; they never compare statuses themselves.
It is pure: no database and no I/O, so the simulation harness can reuse it unchanged.

Each row of _EDGES is (state, action, next state, actor). The actor is the only kind of
party allowed to perform that action from that state; which donor or which acceptor is
checked by the service layer (the donation's own donor, the offered organisation, ...).
Situational rules that hide an edge for a particular donation (an empty slate, an
organisation that cannot collect) live in app.domain.policy, not here.

Terminal states have no outgoing edges. COMPLETED (reuse) and RECYCLED (material
recovery) are the outcomes; CANCELLED is terminal but is a withdrawal, not an outcome.
Nothing ends automatically: a silent donor or a stalled handover goes to NEEDS_ADMIN,
the admin queue, which is a real state with admin exits.

Adding a state means: a value in app.constants.DonationStatus, its rows here, and, if it
ends the lifecycle, membership of TERMINAL_STATES (and OUTCOME_STATES if it is an
outcome). The tests check the table against those sets.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.constants import Actor, DonationAction, DonationStatus

S = DonationStatus
A = DonationAction

INITIAL_STATE = S.LISTED

# fmt: off
_EDGES: tuple[tuple[DonationStatus, DonationAction, DonationStatus, Actor], ...] = (
    # Listed: the donor makes the first offer. No auto-offer; an offer against an empty
    # slate escalates at once, and the sweeper escalates a donation never offered.
    (S.LISTED,           A.OFFER,                 S.MATCHED,          Actor.DONOR),
    (S.LISTED,           A.ESCALATE,              S.ESCALATED,        Actor.SYSTEM),    # empty slate, or LISTED_STALL
    (S.LISTED,           A.CANCEL,                S.CANCELLED,        Actor.DONOR),
    # The donor's choice to recycle instead of donating: never offered to an organisation.
    # Only the "send to recycling" entry point creates a donation straight into this edge
    # (app.services.donations.create_for_recycling); policy hides it on a listed donation.
    (S.LISTED,           A.REDIRECT_TO_RECYCLING, S.WASTE_REDIRECTED, Actor.DONOR),
    # One open offer at a time.
    (S.MATCHED,          A.ACCEPT,                S.ACCEPTED,         Actor.ACCEPTOR),
    (S.MATCHED,          A.REJECT,                S.RE_MATCHING,      Actor.ACCEPTOR),
    (S.MATCHED,          A.EXPIRE,                S.RE_MATCHING,      Actor.SYSTEM),    # sweeper, OFFER_TTL
    (S.MATCHED,          A.CANCEL,                S.CANCELLED,        Actor.DONOR),
    # Transient: resolved in the same transaction that entered it.
    (S.RE_MATCHING,      A.REOFFER,               S.MATCHED,          Actor.SYSTEM),
    (S.RE_MATCHING,      A.ESCALATE,              S.ESCALATED,        Actor.SYSTEM),
    # The donor decides.
    (S.ESCALATED,        A.REMATCH,               S.RE_MATCHING,      Actor.DONOR),
    (S.ESCALATED,        A.UPGRADE_PRIORITY,      S.RE_MATCHING,      Actor.DONOR),
    (S.ESCALATED,        A.REDIRECT_TO_RECYCLING, S.WASTE_REDIRECTED, Actor.DONOR),
    (S.ESCALATED,        A.CANCEL,                S.CANCELLED,        Actor.DONOR),
    (S.ESCALATED,        A.STALL,                 S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper, ESCALATION_TTL
    # Accepted: someone sets the handover time; the mode decides who. Three handover
    # paths: the acceptor collects, the donor delivers, or the donor books a simulated
    # courier (BOOK_PICKUP) — all land in PICKUP_SCHEDULED. The donor picks among the
    # three first; only once ACCEPTOR_PICKUP is the donor's pick does the acceptor's own
    # SCHEDULE_PICKUP open up (app.domain.policy), so both sides see one path, never two
    # competing ones. CHOOSE_ACCEPTOR_COLLECTION is a self-loop, not a new state: it
    # records the donor's choice as data (a StatusEvent on this acceptance, read back by
    # app.services.matching.acceptor_pickup_chosen), the same way a decline or an
    # escalation cause already is, rather than adding a state that every ACCEPTED-aware
    # rule (held states, chat, the refund hook, the sweeper) would need to also know about.
    (S.ACCEPTED,         A.CHOOSE_ACCEPTOR_COLLECTION, S.ACCEPTED,    Actor.DONOR),
    (S.ACCEPTED,         A.SCHEDULE_PICKUP,       S.PICKUP_SCHEDULED, Actor.ACCEPTOR),
    (S.ACCEPTED,         A.CHOOSE_DROPOFF,        S.PICKUP_SCHEDULED, Actor.DONOR),
    (S.ACCEPTED,         A.BOOK_PICKUP,           S.PICKUP_SCHEDULED, Actor.DONOR),
    (S.ACCEPTED,         A.STALL,                 S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper, reneging acceptor
    # Handover: the donor hands over, the acceptor confirms receipt.
    (S.PICKUP_SCHEDULED, A.MARK_HANDED_OVER,      S.IN_TRANSIT,       Actor.DONOR),
    (S.PICKUP_SCHEDULED, A.CONFIRM_RECEIPT,       S.COMPLETED,        Actor.ACCEPTOR),
    (S.PICKUP_SCHEDULED, A.STALL,                 S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper, scheduled_for + grace
    (S.IN_TRANSIT,       A.CONFIRM_RECEIPT,       S.COMPLETED,        Actor.ACCEPTOR),
    (S.IN_TRANSIT,       A.STALL,                 S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper
    # Recycling: only the donor (at listing, or at escalation) or an admin (with a reason)
    # sends a donation here. NO_RECYCLER is immediate, in the same transaction as the
    # redirect. Otherwise the donor moves the goods to the assigned recycler themself
    # (drop-off, or a simulated platform pickup to the recycler's address) before an
    # admin can confirm on the recycler's behalf — there is no recycler login, so
    # nobody else can attest that the goods arrived.
    (S.WASTE_REDIRECTED, A.NO_RECYCLER,           S.NEEDS_ADMIN,      Actor.SYSTEM),    # immediate
    (S.WASTE_REDIRECTED, A.STALL,                 S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper
    (S.WASTE_REDIRECTED, A.DELIVER_TO_RECYCLER,   S.RECYCLING_IN_TRANSIT, Actor.DONOR),
    (S.WASTE_REDIRECTED, A.BOOK_RECYCLER_PICKUP,  S.RECYCLING_IN_TRANSIT, Actor.DONOR),
    # Confirmation is simulated: an admin acts for the recycler, but only once the
    # donor's own handover to the recycler is recorded (never straight from
    # WASTE_REDIRECTED — a deliberate change; see CLAUDE.md Decisions).
    (S.RECYCLING_IN_TRANSIT, A.CONFIRM_RECYCLED,  S.RECYCLED,         Actor.ADMIN),
    (S.RECYCLING_IN_TRANSIT, A.STALL,             S.NEEDS_ADMIN,      Actor.SYSTEM),    # sweeper
    # The admin queue. Every admin action requires a recorded reason.
    (S.NEEDS_ADMIN,      A.REQUEUE,               S.RE_MATCHING,      Actor.ADMIN),
    (S.NEEDS_ADMIN,      A.REDIRECT_TO_RECYCLING, S.WASTE_REDIRECTED, Actor.ADMIN),
    (S.NEEDS_ADMIN,      A.CANCEL,                S.CANCELLED,        Actor.ADMIN),
)
# fmt: on

TRANSITIONS: Mapping[tuple[DonationStatus, DonationAction], DonationStatus] = MappingProxyType(
    {(state, action): target for state, action, target, _ in _EDGES}
)

# Declared beside the table: who may perform each edge.
ACTORS: Mapping[tuple[DonationStatus, DonationAction], Actor] = MappingProxyType(
    {(state, action): actor for state, action, _, actor in _EDGES}
)

# States with no outgoing transition. Declared rather than derived, so the test can
# catch a state that has lost its edges by accident.
TERMINAL_STATES: frozenset[DonationStatus] = frozenset({S.COMPLETED, S.RECYCLED, S.CANCELLED})

# Terminal states that count as an outcome: reuse or material recovery.
OUTCOME_STATES: frozenset[DonationStatus] = frozenset({S.COMPLETED, S.RECYCLED})

# Entered and left within one transaction; a committed donation is never in one.
TRANSIENT_STATES: frozenset[DonationStatus] = frozenset({S.RE_MATCHING})

# States in which the donor may still edit the donation's details and images.
EDITABLE_STATES: frozenset[DonationStatus] = frozenset({S.LISTED})

# States in which the accepting organisation holds the donation: it counts against that
# organisation's capacity, and that organisation may see the precise pickup address.
HELD_STATES: frozenset[DonationStatus] = frozenset({S.ACCEPTED, S.PICKUP_SCHEDULED, S.IN_TRANSIT})

# States in which a platform-arranged pickup booking can exist and be paid for but not
# yet delivered: HELD_STATES (to an organisation) plus RECYCLING_IN_TRANSIT (to a
# recycler). Read only by the sweeper's refund hook — WASTE_REDIRECTED is deliberately
# excluded: address release, capacity, chat and the notification feed all key on
# HELD_STATES alone, and recycling never holds an organisation's slot or address.
BOOKED_STATES: frozenset[DonationStatus] = HELD_STATES | {S.RECYCLING_IN_TRANSIT}


class InvalidTransition(Exception):
    def __init__(self, current: DonationStatus, action: DonationAction) -> None:
        self.current = current
        self.action = action
        super().__init__(f"Cannot {action.value} a donation that is {current.value}.")


class ActorNotAllowed(Exception):
    def __init__(self, current: DonationStatus, action: DonationAction, actor: Actor) -> None:
        super().__init__(
            f"{actor.value} cannot {action.value} a donation that is {current.value}."
        )


def next_state(current: DonationStatus, action: DonationAction) -> DonationStatus:
    """Return the state `action` moves a donation in `current` to, or raise."""
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise InvalidTransition(current, action) from None


def check_actor(current: DonationStatus, action: DonationAction, actor: Actor) -> None:
    """Raise unless `actor` may perform `action` from `current` (which must be an edge)."""
    next_state(current, action)
    if ACTORS[(current, action)] != actor:
        raise ActorNotAllowed(current, action, actor)


def requires_reason(current: DonationStatus, action: DonationAction) -> bool:
    """Every admin action must record why."""
    return ACTORS.get((current, action)) == Actor.ADMIN


def allowed_actions(
    current: DonationStatus, actor: Actor | None = None
) -> frozenset[DonationAction]:
    """Actions leaving `current`; only those `actor` may perform, if given."""
    return frozenset(
        action
        for (state, action), who in ACTORS.items()
        if state == current and (actor is None or who == actor)
    )


def states_awaiting(actor: Actor) -> frozenset[DonationStatus]:
    """States with at least one edge `actor` performs: where a donation waits on them."""
    return frozenset(state for (state, _), who in ACTORS.items() if who == actor)


def successors(current: DonationStatus) -> frozenset[DonationStatus]:
    return frozenset(target for (state, _), target in TRANSITIONS.items() if state == current)


def is_editable(current: DonationStatus) -> bool:
    return current in EDITABLE_STATES
