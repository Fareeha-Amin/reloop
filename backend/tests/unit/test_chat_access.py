"""The chat access rule (app.domain.chat), state by state, for each kind of viewer."""

import pytest

from app.constants import Actor, ChatClosure, DonationStatus
from app.domain import chat, lifecycle

S = DonationStatus

# Where a donation can be after its holder accepted it, without it being completed:
# stalled to the admin queue, and everything an admin or a requeue can lead to.
LEFT_WITHOUT_COMPLETING = [
    S.NEEDS_ADMIN,
    S.RE_MATCHING,
    S.MATCHED,
    S.ESCALATED,
    S.WASTE_REDIRECTED,
    S.RECYCLED,
    S.CANCELLED,
]


@pytest.mark.parametrize("status", sorted(lifecycle.HELD_STATES) + [S.COMPLETED])
@pytest.mark.parametrize("viewer", [Actor.DONOR, Actor.ACCEPTOR])
def test_open_from_acceptance_onward_including_after_completion(viewer, status):
    access = chat.access(viewer, status, is_current_acceptance=True)
    assert access == chat.ThreadAccess(can_read=True, can_write=True, closed_reason=None)


@pytest.mark.parametrize("status", LEFT_WITHOUT_COMPLETING)
@pytest.mark.parametrize("viewer", [Actor.DONOR, Actor.ACCEPTOR])
def test_read_only_once_the_holder_lets_go_without_completing(viewer, status):
    # Still the latest acceptance (no other organisation has accepted since).
    access = chat.access(viewer, status, is_current_acceptance=True)
    assert access == chat.ThreadAccess(can_read=True, can_write=False, closed_reason=ChatClosure.NO_LONGER_HELD)


@pytest.mark.parametrize("status", sorted(S))
def test_after_another_acceptance_the_donor_reads_and_the_old_organisation_loses_the_thread(status):
    donor = chat.access(Actor.DONOR, status, is_current_acceptance=False)
    assert donor == chat.ThreadAccess(can_read=True, can_write=False, closed_reason=ChatClosure.NO_LONGER_HELD)
    assert chat.access(Actor.ACCEPTOR, status, is_current_acceptance=False) == chat.NO_ACCESS


@pytest.mark.parametrize("viewer", [Actor.ADMIN, Actor.SYSTEM])
@pytest.mark.parametrize("status", sorted(S))
def test_admins_and_the_system_have_no_access(viewer, status):
    assert chat.access(viewer, status, is_current_acceptance=True) == chat.NO_ACCESS


def test_open_states_are_the_held_states_and_completion_only():
    assert chat.OPEN_STATES == lifecycle.HELD_STATES | {S.COMPLETED}
    # Every way out of a held state other than completion leads to a closed thread.
    leaving = {
        target
        for state in lifecycle.HELD_STATES
        for target in lifecycle.successors(state)
        if target not in lifecycle.HELD_STATES
    }
    assert leaving - chat.OPEN_STATES == {S.NEEDS_ADMIN}
    assert set(LEFT_WITHOUT_COMPLETING).isdisjoint(chat.OPEN_STATES)
    assert set(LEFT_WITHOUT_COMPLETING) | chat.OPEN_STATES | {S.LISTED} == set(S)
