"""Donation lifecycle — the explicit transition table (non-negotiables 1, 2 and 11).

This module is the only place that decides which status may follow which. Route
handlers and services ask it; they never compare statuses themselves. It is pure: no
database and no I/O, so the simulation harness can reuse it unchanged.

Phase 1 contains a single edge, LISTED --CANCEL--> CANCELLED.

CANCELLED is terminal (no outgoing transitions), but it is a donor withdrawal, not an
outcome. The outcome states COMPLETED (reuse) and RECYCLED (material recovery) arrive in
Phase 2 together with matching, so in Phase 1 a donation that is not cancelled stays
LISTED. That gap is known and is pinned by a strict-xfail test in
tests/unit/test_lifecycle.py, which starts failing once Phase 2 closes the loop.

Adding a state means: a value in `app.constants.DonationStatus`, its edges here, and,
if it ends the lifecycle, membership of TERMINAL_STATES (and OUTCOME_STATES if it is
an outcome). The tests check the table is consistent with those sets.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.constants import DonationAction, DonationStatus

INITIAL_STATE = DonationStatus.LISTED

TRANSITIONS: Mapping[tuple[DonationStatus, DonationAction], DonationStatus] = MappingProxyType(
    {
        (DonationStatus.LISTED, DonationAction.CANCEL): DonationStatus.CANCELLED,
    }
)

# States with no outgoing transition. Declared rather than derived, so the test can
# catch a state that has lost its edges by accident.
TERMINAL_STATES: frozenset[DonationStatus] = frozenset({DonationStatus.CANCELLED})

# Terminal states that count as an outcome (reuse or material recovery). Empty until
# Phase 2 adds COMPLETED and RECYCLED. CANCELLED is deliberately not an outcome.
OUTCOME_STATES: frozenset[DonationStatus] = frozenset()

# States in which the donor may still edit the donation's details and images.
EDITABLE_STATES: frozenset[DonationStatus] = frozenset({DonationStatus.LISTED})


class InvalidTransition(Exception):
    def __init__(self, current: DonationStatus, action: DonationAction) -> None:
        self.current = current
        self.action = action
        super().__init__(f"Cannot {action.value} a donation that is {current.value}.")


def next_state(current: DonationStatus, action: DonationAction) -> DonationStatus:
    """Return the state `action` moves a donation in `current` to, or raise."""
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise InvalidTransition(current, action) from None


def allowed_actions(current: DonationStatus) -> frozenset[DonationAction]:
    return frozenset(action for (state, action) in TRANSITIONS if state == current)


def successors(current: DonationStatus) -> frozenset[DonationStatus]:
    return frozenset(target for (state, _), target in TRANSITIONS.items() if state == current)


def is_editable(current: DonationStatus) -> bool:
    return current in EDITABLE_STATES
