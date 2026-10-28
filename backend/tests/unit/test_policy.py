from datetime import UTC, datetime, timedelta

import pytest

from app.constants import (
    ESCALATION_THRESHOLD,
    ESCALATION_TTL,
    HANDOVER_GRACE,
    LISTED_STALL,
    MAX_RADIUS_KM,
    OFFER_TTL,
    RADIUS_CAP_KM,
    STALL_TIMEOUTS,
    Actor,
    DonationAction,
    DonationStatus,
    EscalationCause,
)
from app.domain import lifecycle
from app.domain.policy import (
    SWEEP_RULES,
    Decision,
    GuardContext,
    SweepFacts,
    available_actions,
    blocked_reason,
    effective_radius_km,
    queue_priority,
    rejection_boost,
    rematch_decision,
    sweep_decision,
)
from app.domain.scoring import MatchingConfig

S, A = DonationStatus, DonationAction
CONFIG = MatchingConfig()
OFF = MatchingConfig(rejection_boost_enabled=False)
T0 = datetime(2030, 1, 1, 9, tzinfo=UTC)


# --- Boosts -------------------------------------------------------------------------------------


def test_radius_widens_per_decline_and_is_capped():
    assert effective_radius_km(0, CONFIG) == MAX_RADIUS_KM
    assert effective_radius_km(1, CONFIG) == pytest.approx(MAX_RADIUS_KM * 1.25)
    assert effective_radius_km(2, CONFIG) == pytest.approx(MAX_RADIUS_KM * 1.5)
    assert effective_radius_km(100, CONFIG) == RADIUS_CAP_KM


def test_rejection_boost_steps_and_cap():
    assert rejection_boost(0, CONFIG) == 1.0
    assert rejection_boost(2, CONFIG) == pytest.approx(1.4)
    assert rejection_boost(100, CONFIG) == CONFIG.rejection_boost_cap


def test_flag_off_disables_both_rejection_effects_but_not_priority():
    assert effective_radius_km(5, OFF) == MAX_RADIUS_KM
    assert rejection_boost(5, OFF) == 1.0
    assert queue_priority(True, 5, OFF) == OFF.priority_boost


def test_queue_priority_multiplies_priority_and_rejection_boost():
    assert queue_priority(False, 0, CONFIG) == 1.0
    assert queue_priority(True, 0, CONFIG) == CONFIG.priority_boost
    assert queue_priority(True, 2, CONFIG) == pytest.approx(CONFIG.priority_boost * 1.4)


# --- Resolving RE_MATCHING ----------------------------------------------------------------------


def test_reoffer_when_nothing_stops_it():
    assert rematch_decision(declines_since_escalation=0, slate_empty=False) == Decision(A.REOFFER)


@pytest.mark.parametrize(
    ("declines", "empty", "cause"),
    [
        (ESCALATION_THRESHOLD, False, EscalationCause.THRESHOLD_REACHED),
        (ESCALATION_THRESHOLD - 1, True, EscalationCause.NO_CANDIDATES),
        (ESCALATION_THRESHOLD, True, EscalationCause.THRESHOLD_REACHED),
    ],
)
def test_escalation_causes(declines, empty, cause):
    decision = rematch_decision(declines_since_escalation=declines, slate_empty=empty)
    assert decision == Decision(A.ESCALATE, cause)


def test_threshold_is_the_default_three():
    assert ESCALATION_THRESHOLD == 3
    assert rematch_decision(declines_since_escalation=2, slate_empty=False).action == A.REOFFER


# --- Guards -------------------------------------------------------------------------------------


def test_empty_slate_leaves_only_recycling_and_cancel_at_escalation():
    actions = available_actions(S.ESCALATED, Actor.DONOR, GuardContext(slate_empty=True))
    assert actions == {A.REDIRECT_TO_RECYCLING, A.CANCEL}


def test_non_empty_slate_offers_every_escalation_choice():
    actions = available_actions(S.ESCALATED, Actor.DONOR, GuardContext(slate_empty=False))
    assert actions == {A.REMATCH, A.UPGRADE_PRIORITY, A.REDIRECT_TO_RECYCLING, A.CANCEL}


def test_upgrade_priority_hidden_when_already_priority():
    actions = available_actions(S.ESCALATED, Actor.DONOR, GuardContext(slate_empty=False, is_priority=True))
    assert A.UPGRADE_PRIORITY not in actions and A.REMATCH in actions


def test_admin_queue_guards():
    stuck = GuardContext(slate_empty=True, recycler_available=False)
    assert available_actions(S.NEEDS_ADMIN, Actor.ADMIN, stuck) == {A.CANCEL}
    free = GuardContext(slate_empty=False, recycler_available=True)
    assert available_actions(S.NEEDS_ADMIN, Actor.ADMIN, free) == {A.REQUEUE, A.REDIRECT_TO_RECYCLING, A.CANCEL}


def test_schedule_pickup_hidden_for_an_organisation_that_does_not_collect():
    assert blocked_reason(S.ACCEPTED, A.SCHEDULE_PICKUP, GuardContext(pickup_capable=False))
    # Even a collecting organisation has no schedule action until the donor chooses it.
    assert blocked_reason(S.ACCEPTED, A.SCHEDULE_PICKUP, GuardContext(pickup_capable=True))
    assert (
        blocked_reason(
            S.ACCEPTED, A.SCHEDULE_PICKUP, GuardContext(pickup_capable=True, donor_chose_acceptor_pickup=True)
        )
        is None
    )


def test_choose_acceptor_collection_hidden_once_chosen_or_if_the_organisation_cannot_collect():
    assert blocked_reason(S.ACCEPTED, A.CHOOSE_ACCEPTOR_COLLECTION, GuardContext(pickup_capable=False))
    assert blocked_reason(
        S.ACCEPTED, A.CHOOSE_ACCEPTOR_COLLECTION, GuardContext(pickup_capable=True, donor_chose_acceptor_pickup=True)
    )
    assert (
        blocked_reason(S.ACCEPTED, A.CHOOSE_ACCEPTOR_COLLECTION, GuardContext(pickup_capable=True)) is None
    )


@pytest.mark.parametrize("action", [A.CHOOSE_DROPOFF, A.BOOK_PICKUP])
def test_the_donors_other_two_paths_are_hidden_once_acceptor_pickup_is_chosen(action):
    assert blocked_reason(S.ACCEPTED, action, GuardContext(donor_chose_acceptor_pickup=True))
    assert blocked_reason(S.ACCEPTED, action, GuardContext(donor_chose_acceptor_pickup=False)) is None
    assert blocked_reason(S.ACCEPTED, action, GuardContext()) is None  # not computed never blocks


def test_book_pickup_hidden_with_no_active_logistics_provider():
    assert blocked_reason(S.ACCEPTED, A.BOOK_PICKUP, GuardContext(logistics_available=False))
    assert blocked_reason(S.ACCEPTED, A.BOOK_PICKUP, GuardContext(logistics_available=True)) is None
    # Unknown (not computed) never blocks, same as the other guards.
    assert blocked_reason(S.ACCEPTED, A.BOOK_PICKUP, GuardContext()) is None


def test_guards_never_add_actions_the_table_does_not_allow():
    ctx = GuardContext(slate_empty=False, recycler_available=True, pickup_capable=True)
    for state in DonationStatus:
        for actor in Actor:
            assert available_actions(state, actor, ctx) <= lifecycle.allowed_actions(state, actor)


# --- Sweeper rules ------------------------------------------------------------------------------


def facts(status, entered=T0, expires=None, handover=None) -> SweepFacts:
    return SweepFacts(status=status, entered_at=entered, offer_expires_at=expires, handover_at=handover)


def test_listed_never_offered_escalates_after_listed_stall():
    assert LISTED_STALL == timedelta(days=7)
    f = facts(S.LISTED)
    assert sweep_decision(f, T0 + LISTED_STALL - timedelta(seconds=1)) is None
    assert sweep_decision(f, T0 + LISTED_STALL) == Decision(A.ESCALATE, EscalationCause.NOT_OFFERED)


def test_the_pickup_window_is_not_a_sweep_fact():
    """Advisory only: nothing the sweeper decides can depend on it."""
    assert "window_end" not in SweepFacts.__dataclass_fields__


def test_offer_expires_at_its_ttl():
    f = facts(S.MATCHED, expires=T0 + OFFER_TTL)
    assert sweep_decision(f, T0 + OFFER_TTL - timedelta(seconds=1)) is None
    assert sweep_decision(f, T0 + OFFER_TTL) == Decision(A.EXPIRE)


def test_pickup_scheduled_stalls_relative_to_the_handover_time():
    handover = T0 + timedelta(days=5)
    f = facts(S.PICKUP_SCHEDULED, handover=handover)
    assert sweep_decision(f, handover + HANDOVER_GRACE - timedelta(seconds=1)) is None
    assert sweep_decision(f, handover + HANDOVER_GRACE) == Decision(A.STALL)


@pytest.mark.parametrize(
    ("status", "timeout"),
    [
        (S.ESCALATED, ESCALATION_TTL),
        (S.ACCEPTED, STALL_TIMEOUTS[S.ACCEPTED]),
        (S.IN_TRANSIT, STALL_TIMEOUTS[S.IN_TRANSIT]),
        (S.WASTE_REDIRECTED, STALL_TIMEOUTS[S.WASTE_REDIRECTED]),
    ],
)
def test_stall_timeouts(status, timeout):
    f = facts(status)
    assert sweep_decision(f, T0 + timeout - timedelta(seconds=1)) is None
    assert sweep_decision(f, T0 + timeout) == Decision(A.STALL)


@pytest.mark.parametrize("status", [S.NEEDS_ADMIN, S.COMPLETED, S.RECYCLED, S.CANCELLED])
def test_admin_queue_and_terminal_states_are_never_swept(status):
    assert sweep_decision(facts(status), T0 + timedelta(days=365)) is None


def test_every_decision_is_an_edge_of_the_table():
    """Whatever the sweeper decides must be a SYSTEM edge from that state."""
    late = T0 + timedelta(days=365)
    for status in DonationStatus:
        d = sweep_decision(facts(status, expires=T0 + OFFER_TTL, handover=T0), late)
        if d is not None:
            assert lifecycle.ACTORS[(status, d.action)] == Actor.SYSTEM
            assert d.action in SWEEP_RULES[status]


def test_a_listed_donation_cannot_be_sent_to_recycling_from_its_page():
    """The donor's choice is made when the donation is created, not on a listed one."""
    assert blocked_reason(S.LISTED, A.REDIRECT_TO_RECYCLING, GuardContext()) is not None
    assert A.REDIRECT_TO_RECYCLING not in available_actions(S.LISTED, Actor.DONOR, GuardContext())
    assert available_actions(S.LISTED, Actor.DONOR, GuardContext()) == {A.OFFER, A.CANCEL}


def test_handover_options_are_empty_until_the_donor_chooses_acceptor_pickup():
    """Before any choice, the three paths ARE the donor's own allowed_actions
    (CHOOSE_ACCEPTOR_COLLECTION, CHOOSE_DROPOFF, BOOK_PICKUP) — nothing informational
    to add. Once chosen, this names the one path waiting to be scheduled."""
    from app.constants import HandoverMode
    from app.domain.policy import handover_options

    assert handover_options(S.ACCEPTED, donor_chose_acceptor_pickup=False) == ()

    chosen = handover_options(S.ACCEPTED, donor_chose_acceptor_pickup=True)
    assert len(chosen) == 1
    assert (chosen[0].path, chosen[0].available, chosen[0].you_do_it) == (HandoverMode.ACCEPTOR_PICKUP, True, False)

    for state in (S.PICKUP_SCHEDULED, S.IN_TRANSIT, S.COMPLETED, S.LISTED):
        assert handover_options(state, donor_chose_acceptor_pickup=True) == ()
