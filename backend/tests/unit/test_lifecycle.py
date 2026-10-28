"""The transition table is the product's central claim. These tests are written against
the declared sets, not against specific states, so they keep holding as states are added."""

from collections import deque

import pytest

from app.constants import Actor, DonationAction, DonationStatus
from app.domain import lifecycle, policy
from app.domain.lifecycle import (
    ACTORS,
    EDITABLE_STATES,
    HELD_STATES,
    INITIAL_STATE,
    OUTCOME_STATES,
    TERMINAL_STATES,
    TRANSIENT_STATES,
    TRANSITIONS,
    ActorNotAllowed,
    InvalidTransition,
    allowed_actions,
    check_actor,
    is_editable,
    next_state,
    requires_reason,
    successors,
)

S, A = DonationStatus, DonationAction
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


# --- Shape of the table -----------------------------------------------------------------------


def test_table_only_uses_known_states_and_actions():
    for (state, action), target in TRANSITIONS.items():
        assert state in ALL_STATES
        assert target in ALL_STATES
        assert action in frozenset(DonationAction)


def test_every_action_is_used():
    assert {action for _, action in TRANSITIONS} == set(DonationAction)


def test_every_edge_declares_exactly_one_actor():
    assert set(ACTORS) == set(TRANSITIONS)
    assert all(actor in frozenset(Actor) for actor in ACTORS.values())


def test_table_is_read_only():
    with pytest.raises(TypeError):
        lifecycle.TRANSITIONS[(S.CANCELLED, A.CANCEL)] = S.LISTED
    with pytest.raises(TypeError):
        lifecycle.ACTORS[(S.LISTED, A.CANCEL)] = Actor.ADMIN


# --- Non-negotiable 1: no dead ends ------------------------------------------------------------


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


@pytest.mark.parametrize("state", sorted(NON_TERMINAL))
def test_every_non_terminal_state_can_reach_an_outcome(state):
    """The Phase 1 strict xfail on this test is gone: the loop is closed."""
    assert reachable_from(state) & OUTCOME_STATES, f"{state} cannot reach reuse or recovery"


def test_outcomes_are_completed_and_recycled_and_cancelled_is_not_one():
    assert OUTCOME_STATES == {S.COMPLETED, S.RECYCLED}
    assert TERMINAL_STATES == OUTCOME_STATES | {S.CANCELLED}


def test_there_is_no_expired_state_and_no_delivered_state():
    names = {s.value for s in DonationStatus}
    assert "EXPIRED" not in names and "DELIVERED" not in names


def test_nothing_reaches_a_terminal_state_without_a_person():
    """No deadline and no empty slate ends a donation: SYSTEM never moves one into a
    terminal state. A silent donor goes to NEEDS_ADMIN instead."""
    for (state, action), target in TRANSITIONS.items():
        if target in TERMINAL_STATES:
            assert ACTORS[(state, action)] != Actor.SYSTEM, (state, action)


def test_only_donor_or_admin_consents_to_recycling():
    into_recycling = {key for key, target in TRANSITIONS.items() if target == S.WASTE_REDIRECTED}
    assert {ACTORS[k] for k in into_recycling} == {Actor.DONOR, Actor.ADMIN}
    # The donor sends a listed donation here at creation, or an escalated one later.
    assert {state for state, _ in into_recycling} == {S.LISTED, S.ESCALATED, S.NEEDS_ADMIN}


def test_a_listed_donation_goes_to_recycling_only_by_the_donor():
    """The donor's own choice: one edge, never offered to an organisation."""
    assert ACTORS[(S.LISTED, A.REDIRECT_TO_RECYCLING)] == Actor.DONOR
    assert TRANSITIONS[(S.LISTED, A.REDIRECT_TO_RECYCLING)] == S.WASTE_REDIRECTED
    assert {state for state, action in TRANSITIONS if action == A.REDIRECT_TO_RECYCLING} == {
        S.LISTED,
        S.ESCALATED,
        S.NEEDS_ADMIN,
    }


# --- Waiting states and the sweeper -------------------------------------------------------------

# States that wait on a person (donor, acceptor, recycler) rather than on the system.
WAITING_STATES = NON_TERMINAL - TRANSIENT_STATES


@pytest.mark.parametrize("state", sorted(WAITING_STATES))
def test_every_waiting_state_has_a_sweeper_or_admin_exit(state):
    sweeper_exit = state in policy.SWEEP_RULES
    admin_exit = any(ACTORS[(state, a)] == Actor.ADMIN for a in allowed_actions(state))
    assert sweeper_exit or admin_exit, f"{state} could wait forever"


@pytest.mark.parametrize(("state", "actions"), sorted(policy.SWEEP_RULES.items()))
def test_sweep_rules_are_system_edges_of_the_table(state, actions):
    for action in actions:
        assert ACTORS[(state, action)] == Actor.SYSTEM, (state, action)


def test_the_admin_queue_is_left_only_by_admins():
    assert allowed_actions(S.NEEDS_ADMIN) == allowed_actions(S.NEEDS_ADMIN, Actor.ADMIN)
    assert S.NEEDS_ADMIN not in policy.SWEEP_RULES


@pytest.mark.parametrize("state", sorted(TRANSIENT_STATES))
def test_transient_states_are_resolved_by_the_system_alone(state):
    assert allowed_actions(state) == allowed_actions(state, Actor.SYSTEM)
    assert state not in policy.SWEEP_RULES  # never committed, so never swept


# --- Actors and reasons ----------------------------------------------------------------------------


def test_admin_actions_require_a_reason_and_no_others_do():
    for (state, action), actor in ACTORS.items():
        assert requires_reason(state, action) == (actor == Actor.ADMIN)


def test_check_actor():
    check_actor(S.MATCHED, A.ACCEPT, Actor.ACCEPTOR)
    with pytest.raises(ActorNotAllowed):
        check_actor(S.MATCHED, A.ACCEPT, Actor.DONOR)
    with pytest.raises(InvalidTransition):
        check_actor(S.LISTED, A.ACCEPT, Actor.ACCEPTOR)


def test_cancel_is_the_donors_until_acceptance_then_only_an_admins():
    donor_cancel = {s for (s, a), who in ACTORS.items() if a == A.CANCEL and who == Actor.DONOR}
    assert donor_cancel == {S.LISTED, S.MATCHED, S.ESCALATED}
    assert ACTORS[(S.NEEDS_ADMIN, A.CANCEL)] == Actor.ADMIN


def test_handover_roles_are_fixed():
    assert ACTORS[(S.PICKUP_SCHEDULED, A.MARK_HANDED_OVER)] == Actor.DONOR
    assert ACTORS[(S.PICKUP_SCHEDULED, A.CONFIRM_RECEIPT)] == Actor.ACCEPTOR
    assert ACTORS[(S.IN_TRANSIT, A.CONFIRM_RECEIPT)] == Actor.ACCEPTOR


def test_choose_acceptor_collection_is_a_self_loop_recording_the_donors_choice():
    """Data, not a state: the donor's choice is read back from the event log
    (app.services.matching.acceptor_pickup_chosen), not from where the table sent it."""
    assert TRANSITIONS[(S.ACCEPTED, A.CHOOSE_ACCEPTOR_COLLECTION)] == S.ACCEPTED
    assert ACTORS[(S.ACCEPTED, A.CHOOSE_ACCEPTOR_COLLECTION)] == Actor.DONOR
    # A self-loop does not break reachability: ACCEPTED can still reach COMPLETED.
    assert S.COMPLETED in reachable_from(S.ACCEPTED)


def test_three_handover_paths_all_reach_pickup_scheduled():
    into_pickup_scheduled = {a for (s, a), t in TRANSITIONS.items() if s == S.ACCEPTED and t == S.PICKUP_SCHEDULED}
    assert into_pickup_scheduled == {A.SCHEDULE_PICKUP, A.CHOOSE_DROPOFF, A.BOOK_PICKUP}
    assert ACTORS[(S.ACCEPTED, A.SCHEDULE_PICKUP)] == Actor.ACCEPTOR
    assert ACTORS[(S.ACCEPTED, A.CHOOSE_DROPOFF)] == Actor.DONOR
    assert ACTORS[(S.ACCEPTED, A.BOOK_PICKUP)] == Actor.DONOR


def test_no_withdraw_and_no_auto_offer():
    assert "WITHDRAW" not in {a.value for a in DonationAction}
    assert ACTORS[(S.LISTED, A.OFFER)] == Actor.DONOR


def test_allowed_actions_per_actor():
    assert allowed_actions(S.LISTED, Actor.DONOR) == {A.OFFER, A.CANCEL, A.REDIRECT_TO_RECYCLING}
    assert allowed_actions(S.LISTED, Actor.SYSTEM) == {A.ESCALATE}
    assert allowed_actions(S.MATCHED, Actor.ACCEPTOR) == {A.ACCEPT, A.REJECT}
    assert allowed_actions(S.CANCELLED) == frozenset()


# --- Single edges --------------------------------------------------------------------------------


def test_cancel_moves_listed_to_cancelled():
    assert next_state(S.LISTED, A.CANCEL) == S.CANCELLED


def test_cancelling_twice_is_rejected():
    with pytest.raises(InvalidTransition):
        next_state(S.CANCELLED, A.CANCEL)


def test_rejection_and_expiry_go_through_re_matching():
    assert next_state(S.MATCHED, A.REJECT) == S.RE_MATCHING
    assert next_state(S.MATCHED, A.EXPIRE) == S.RE_MATCHING
    assert successors(S.RE_MATCHING) == {S.MATCHED, S.ESCALATED}


def test_only_listed_and_re_matching_escalate():
    """The pickup window is advisory: no state escalates because it lapsed."""
    assert {state for state, action in TRANSITIONS if action == A.ESCALATE} == {S.LISTED, S.RE_MATCHING}


# --- Declared sets ---------------------------------------------------------------------------------


def test_editable_states_are_not_terminal():
    assert EDITABLE_STATES <= NON_TERMINAL
    assert is_editable(S.LISTED)
    assert not is_editable(S.CANCELLED)


def test_held_states_follow_acceptance_and_precede_completion():
    assert HELD_STATES == {S.ACCEPTED, S.PICKUP_SCHEDULED, S.IN_TRANSIT}
    assert HELD_STATES <= NON_TERMINAL - TRANSIENT_STATES


def test_only_stall_leaves_held_states_without_completing():
    """Phase 4: a platform-pickup booking exists only while a donation holds
    lifecycle.HELD_STATES, and app.services.sweeper cancels and refunds it at exactly
    one edge, STALL. Driven off the table (not a hand-written list of states), so a
    future edge that bypasses STALL — e.g. a direct admin CANCEL from ACCEPTED — fails
    this test instead of silently leaving a paid, undelivered booking unrefunded."""
    for (state, action), target in TRANSITIONS.items():
        if state in HELD_STATES and target not in HELD_STATES and target != S.COMPLETED:
            assert action == A.STALL, f"{state} --{action}--> {target} leaves a held donation unrefunded"


def test_states_awaiting_an_admin_are_the_queue_and_recycling_confirmation():
    """The admin's notification feed is derived from this."""
    assert lifecycle.states_awaiting(Actor.ADMIN) == {DonationStatus.NEEDS_ADMIN, DonationStatus.WASTE_REDIRECTED}
    assert not lifecycle.states_awaiting(Actor.ADMIN) & TERMINAL_STATES
