"""The transition table is the product's central claim. These tests are written against
the declared sets, not against today's specific states, so they keep holding as Phase 2
adds states."""

from collections import deque

import pytest

from app.constants import DonationAction, DonationStatus
from app.domain import lifecycle
from app.domain.lifecycle import (
    EDITABLE_STATES,
    INITIAL_STATE,
    OUTCOME_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    InvalidTransition,
    allowed_actions,
    is_editable,
    next_state,
    successors,
)

ALL_STATES = frozenset(DonationStatus)
NON_TERMINAL = ALL_STATES - TERMINAL_STATES


def reachable_from(start: DonationStatus) -> set[DonationStatus]:
    seen, queue = {start}, deque([start])
    while queue:
        for nxt in successors(queue.popleft()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def test_table_only_uses_known_states_and_actions():
    for (state, action), target in TRANSITIONS.items():
        assert state in ALL_STATES
        assert target in ALL_STATES
        assert action in frozenset(DonationAction)


@pytest.mark.parametrize("state", sorted(NON_TERMINAL))
def test_every_non_terminal_state_has_an_outgoing_transition(state):
    assert successors(state), f"{state} can be entered but never left"


@pytest.mark.parametrize("state", sorted(TERMINAL_STATES))
def test_terminal_states_have_no_outgoing_transitions(state):
    assert successors(state) == frozenset()


def test_declared_terminal_states_are_exactly_the_states_without_edges():
    without_edges = {s for s in ALL_STATES if not successors(s)}
    assert without_edges == TERMINAL_STATES


def test_every_state_is_reachable_from_the_initial_state():
    assert reachable_from(INITIAL_STATE) == ALL_STATES


def test_outcomes_are_terminal_and_cancelled_is_not_an_outcome():
    assert OUTCOME_STATES <= TERMINAL_STATES
    assert DonationStatus.CANCELLED in TERMINAL_STATES
    assert DonationStatus.CANCELLED not in OUTCOME_STATES


def test_editable_states_are_not_terminal():
    assert EDITABLE_STATES <= NON_TERMINAL
    assert is_editable(DonationStatus.LISTED)
    assert not is_editable(DonationStatus.CANCELLED)


def test_cancel_moves_listed_to_cancelled():
    assert next_state(DonationStatus.LISTED, DonationAction.CANCEL) == DonationStatus.CANCELLED


def test_cancelling_twice_is_rejected():
    with pytest.raises(InvalidTransition):
        next_state(DonationStatus.CANCELLED, DonationAction.CANCEL)


def test_allowed_actions():
    assert allowed_actions(DonationStatus.LISTED) == {DonationAction.CANCEL}
    assert allowed_actions(DonationStatus.CANCELLED) == frozenset()


def test_table_is_read_only():
    with pytest.raises(TypeError):
        lifecycle.TRANSITIONS[(DonationStatus.CANCELLED, DonationAction.CANCEL)] = DonationStatus.LISTED


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known Phase 1 gap: outcome states (COMPLETED, RECYCLED) arrive in Phase 2, so a "
        "LISTED donation cannot yet reach reuse or recovery. strict=True: once Phase 2 "
        "closes the loop this XPASSes and fails the run, so remove this marker then."
    ),
)
@pytest.mark.parametrize("state", sorted(NON_TERMINAL))
def test_every_non_terminal_state_can_reach_an_outcome(state):
    assert reachable_from(state) & OUTCOME_STATES
