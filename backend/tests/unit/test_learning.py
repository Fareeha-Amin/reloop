"""Learned ranking weights: pure fitting, the holdout split, the gate. No database."""

import math
import random
import uuid

import numpy as np
import pytest

import app.domain.learning as learning
from app.constants import MODEL_COEF_MAX, SCORE_WEIGHTS, ScoreFactor
from app.domain.learning import FACTORS, Evaluation, Outcome, gate, in_holdout, prior_vector, ranking_weights
from app.domain.scoring import MatchingConfig

TRUE = {
    ScoreFactor.PROXIMITY: 4.0,
    ScoreFactor.NEED_MATCH: 2.0,
    ScoreFactor.URGENCY: 0.5,
    ScoreFactor.CAPACITY_HEADROOM: 0.5,
    ScoreFactor.ACCEPTANCE_RATE: 1.0,
}


def planted(n: int, seed: int, *, coefficients=TRUE, intercept=-4.5, donations=None) -> list[Outcome]:
    """Offers whose outcomes follow a known logistic model. Groups are donation ids."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        features = tuple(rng.random() for _ in FACTORS)
        z = intercept + sum(coefficients[f] * x for f, x in zip(FACTORS, features))
        accepted = rng.random() < 1 / (1 + math.exp(-z))
        group = donations[i] if donations else f"donation-{i // 3}"
        rows.append(Outcome(group=group, features=features, accepted=accepted))
    return rows


# --- Cold start -------------------------------------------------------------------------------


def test_the_prior_vector_is_score_weights_in_factor_order():
    assert list(prior_vector()) == [SCORE_WEIGHTS[f] for f in FACTORS]


def test_normalised_prior_is_score_weights_exactly():
    """Cold start: the prior, normalised, is SCORE_WEIGHTS (they already sum to 1)."""
    normalised = ranking_weights(prior_vector())
    for f in ScoreFactor:
        assert normalised[f] == pytest.approx(SCORE_WEIGHTS[f], abs=1e-12)


def test_no_data_means_no_fit_and_the_prior_stays():
    evaluation = learning.evaluate([], bootstrap=0)
    assert evaluation.weights is None
    assert evaluation.prior_weights == {f: SCORE_WEIGHTS[f] for f in FACTORS}
    assert not gate(evaluation, real_n=0, real_accepted=0, real_declined=0, sandbox=False).activate


def test_a_single_class_cannot_be_fitted():
    rows = [Outcome(f"d{i}", (0.5,) * 5, accepted=True) for i in range(40)]
    evaluation = learning.evaluate(rows, bootstrap=0)
    assert evaluation.weights is None
    assert any("no fit" in note for note in evaluation.notes)


# --- The bounded MAP fit ----------------------------------------------------------------------


def test_planted_effects_move_the_weights_in_the_expected_direction():
    evaluation = learning.evaluate(planted(3000, seed=1), bootstrap=0)
    assert evaluation.weights is not None
    # Proximity carries the largest planted effect, so it must rise above its prior 0.30.
    assert evaluation.weights[ScoreFactor.PROXIMITY] > SCORE_WEIGHTS[ScoreFactor.PROXIMITY]
    assert evaluation.weights[ScoreFactor.PROXIMITY] == max(evaluation.weights.values())


def test_fitted_weights_are_non_negative_and_sum_to_one():
    evaluation = learning.evaluate(planted(3000, seed=2), bootstrap=0)
    assert all(w >= 0 for w in evaluation.weights.values())
    assert math.isclose(sum(evaluation.weights.values()), 1.0, abs_tol=1e-12)
    # The config accepts them (it validates the sum and the sign).
    MatchingConfig(weights=evaluation.weights)


def test_coefficients_stay_within_the_bounds():
    evaluation = learning.evaluate(planted(2000, seed=3), bootstrap=0)
    assert np.all(evaluation.beta >= 0) and np.all(evaluation.beta <= MODEL_COEF_MAX)


def test_a_bound_can_bind_and_the_factor_keeps_its_component_at_weight_zero():
    """A factor with a negative true effect is pushed to the lower bound. Its weight is 0,
    and it stays in the breakdown: the component is shown, with contribution 0."""
    coefficients = {**TRUE, ScoreFactor.URGENCY: -2.0}
    evaluation = learning.evaluate(planted(3000, seed=4, coefficients=coefficients), bootstrap=0)
    assert evaluation.weights is not None
    assert evaluation.weights[ScoreFactor.URGENCY] == pytest.approx(0.0, abs=1e-6)
    assert set(evaluation.weights) == set(ScoreFactor)
    assert evaluation.unconstrained is not None
    assert evaluation.unconstrained[FACTORS.index(ScoreFactor.URGENCY)] < 0  # the bound is what binds


def test_the_prior_penalty_pulls_the_fit_to_the_prior(monkeypatch):
    monkeypatch.setattr(learning, "MODEL_PRIOR_PENALTY", 1e9)
    evaluation = learning.evaluate(planted(2000, seed=5), bootstrap=0)
    for f in FACTORS:
        assert evaluation.beta[FACTORS.index(f)] == pytest.approx(SCORE_WEIGHTS[f], abs=1e-3)


def test_intervals_are_ordered_and_cover_every_factor():
    evaluation = learning.evaluate(planted(1200, seed=6), bootstrap=20)
    assert evaluation.intervals is not None
    assert set(evaluation.intervals) == set(ScoreFactor)
    for low, high in evaluation.intervals.values():
        assert 0 <= low <= high <= 1


def test_the_sklearn_comparison_is_recorded_and_agrees_in_sign_when_no_bound_binds():
    evaluation = learning.evaluate(planted(3000, seed=7), bootstrap=0)
    assert evaluation.unconstrained is not None
    for f in FACTORS:
        assert np.sign(evaluation.unconstrained[FACTORS.index(f)]) == np.sign(TRUE[f])


def test_the_normalised_ranking_keeps_the_order_of_the_fitted_probability():
    """Normalising divides by a positive constant and the intercept is shared within a
    donation, so ranking by the normalised weights equals ranking by the fitted logit."""
    evaluation = learning.evaluate(planted(3000, seed=8), bootstrap=0)
    rng = np.random.default_rng(0)
    for _ in range(200):
        candidates = rng.random((6, len(FACTORS)))
        raw = candidates @ evaluation.beta
        normalised = candidates @ np.array([evaluation.weights[f] for f in FACTORS])
        assert list(np.argsort(-raw, kind="stable")) == list(np.argsort(-normalised, kind="stable"))


# --- The holdout split --------------------------------------------------------------------


def test_the_split_is_deterministic_and_about_the_configured_fraction():
    groups = [str(uuid.UUID(int=i)) for i in range(4000)]
    assert [in_holdout(g) for g in groups] == [in_holdout(g) for g in groups]
    share = sum(in_holdout(g) for g in groups) / len(groups)
    assert 0.20 < share < 0.30


def test_all_offers_of_a_donation_fall_on_one_side():
    rows = planted(600, seed=9)
    sides: dict[str, set[bool]] = {}
    for row in rows:
        sides.setdefault(row.group, set()).add(in_holdout(row.group))
    assert all(len(s) == 1 for s in sides.values())


# --- The real-outcome floor and the gate ---------------------------------------------------------


@pytest.mark.parametrize(
    ("n", "accepted", "declined", "met"),
    [
        (100, 20, 80, True),
        (99, 20, 79, False),  # one short of the total
        (100, 19, 81, False),  # one short of the accepted class
        (100, 81, 19, False),  # one short of the declined class
    ],
)
def test_the_floor_is_total_and_per_class(n, accepted, declined, met):
    assert (learning.floor_reason(n, accepted, declined) is None) is met


def _evaluation(fitted: float | None, prior: float | None, weights=None) -> Evaluation:
    return Evaluation(
        train_n=100,
        holdout_n=25,
        beta=np.array([0.3] * 5) if weights is not None else None,
        intercept=0.0,
        weights=weights,
        prior_weights=dict(SCORE_WEIGHTS),
        fitted_loss=fitted,
        prior_loss=prior,
        fitted_auc=None,
        prior_auc=None,
        unconstrained=None,
    )


WEIGHTS = dict(SCORE_WEIGHTS)


def test_the_gate_activates_only_past_the_floor_and_when_the_holdout_beats_the_prior():
    ok = gate(_evaluation(0.50, 0.60, WEIGHTS), real_n=120, real_accepted=40, real_declined=80, sandbox=False)
    assert ok.activate and ok.reasons == ()


def test_the_gate_refuses_below_the_floor_even_with_a_better_fit():
    result = gate(_evaluation(0.50, 0.60, WEIGHTS), real_n=32, real_accepted=13, real_declined=19, sandbox=False)
    assert not result.activate
    assert any("floor" in r for r in result.reasons)


def test_the_gate_refuses_a_fit_that_does_not_beat_the_prior():
    result = gate(_evaluation(0.61, 0.60, WEIGHTS), real_n=120, real_accepted=40, real_declined=80, sandbox=False)
    assert not result.activate
    assert any("does not beat the prior" in r for r in result.reasons)


def test_the_gate_never_activates_a_sandbox_fit_however_good():
    result = gate(_evaluation(0.10, 0.60, WEIGHTS), real_n=500, real_accepted=200, real_declined=300, sandbox=True)
    assert not result.activate
    assert any("sandbox" in r for r in result.reasons)


def test_the_gate_needs_held_out_outcomes_to_compare():
    result = gate(_evaluation(None, None, WEIGHTS), real_n=120, real_accepted=40, real_declined=80, sandbox=False)
    assert not result.activate
    assert any("no held-out outcomes" in r for r in result.reasons)


def test_all_zero_coefficients_have_no_ranking_weights():
    with pytest.raises(ValueError):
        ranking_weights(np.zeros(5))


# --- The demo gate (test database only; see app.services.training.demo_fit) ---------------------


def test_the_demo_gate_needs_no_floor_but_still_needs_to_beat_the_prior_on_the_holdout():
    assert learning.demo_gate(_evaluation(0.50, 0.60, WEIGHTS)).activate
    worse = learning.demo_gate(_evaluation(0.61, 0.60, WEIGHTS))
    assert not worse.activate and any("does not beat the prior" in r for r in worse.reasons)
    assert not learning.demo_gate(_evaluation(None, None, WEIGHTS)).activate
    assert not learning.demo_gate(_evaluation(None, None, None)).activate


def test_the_production_gate_still_refuses_synthetic_data_however_good():
    """The demo exception is a separate function. The production gate is unchanged."""
    result = gate(_evaluation(0.10, 0.60, WEIGHTS), real_n=500, real_accepted=200, real_declined=300, sandbox=True)
    assert not result.activate
