"""The simulation harness: it runs the real modules, and its outcomes support the fitting
pipeline. The acceptance model it draws from is an assumption (sim/truth.py); these tests
check the pipeline, not real behaviour."""

import ast
from pathlib import Path

import pytest

import app.domain.lifecycle as lifecycle_module
import app.domain.policy as policy_module
import app.domain.scoring as scoring_module
from app.constants import SCORE_WEIGHTS, ScoreFactor
from app.domain import learning
from sim import engine, world
from sim.truth import TRUE_MODEL

SIM_DIR = Path(engine.__file__).resolve().parent


def test_the_engine_uses_the_real_modules_by_identity():
    assert engine.scoring is scoring_module
    assert engine.policy is policy_module
    assert engine.lifecycle is lifecycle_module


def test_every_ranking_goes_through_the_real_scoring_function(monkeypatch):
    calls = []
    real_rank = scoring_module.rank

    def counting_rank(*args, **kwargs):
        calls.append(1)
        return real_rank(*args, **kwargs)

    monkeypatch.setattr(scoring_module, "rank", counting_rank)
    generated = world.generate(11, orgs=10, donations=12)
    engine.run(generated, 11)
    # At least one ranking per donation, and re-matching ranks again after a decline.
    assert len(calls) >= len(generated.donations)


def test_the_sim_defines_no_scoring_or_transition_logic_of_its_own():
    forbidden = {
        "rank",
        "score_components",
        "hard_filter",
        "acceptance_rate",
        "next_state",
        "rematch_decision",
        "effective_radius_km",
        "haversine_km",
    }
    offenders = []
    for path in SIM_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.ClassDef) and node.name in forbidden:
                offenders.append(f"{path.name}:{node.lineno} {node.name}")
    assert not offenders, "sim/ must call the real modules, not define them:\n" + "\n".join(offenders)


def test_the_same_seed_gives_the_same_outcomes_and_another_seed_does_not():
    first = engine.run(world.generate(3, orgs=12, donations=30), 3)
    again = engine.run(world.generate(3, orgs=12, donations=30), 3)
    other = engine.run(world.generate(4, orgs=12, donations=30), 4)
    assert first == again
    assert first != other


def test_outcomes_are_well_formed():
    offers = engine.run(world.generate(5, orgs=20, donations=150), 5)
    assert offers
    for offer in offers:
        assert len(offer.features) == len(learning.FACTORS)
        assert all(0.0 <= x <= 1.0 for x in offer.features)
    # Within a donation, the offer that is accepted is its last one: it ends the donation.
    by_donation: dict = {}
    for offer in offers:
        by_donation.setdefault(offer.donation_ref, []).append(offer)
    for donated in by_donation.values():
        accepted_positions = [i for i, o in enumerate(donated) if o.accepted]
        assert len(accepted_positions) <= 1
        if accepted_positions:
            assert accepted_positions[0] == len(donated) - 1


def test_a_declined_organisation_is_never_offered_the_same_donation_again():
    offers = engine.run(world.generate(6, orgs=15, donations=120), 6)
    seen: set = set()
    for offer in offers:
        key = (offer.donation_ref, offer.organization_ref)
        assert key not in seen
        seen.add(key)


def test_fitting_recovers_the_planted_direction():
    """The pipeline, end to end on synthetic outcomes: the fit should move proximity up
    from its prior, the largest planted effect. Says nothing about real acceptors."""
    offers = engine.run(world.generate(21, orgs=40, donations=1500), 21)
    pool = [
        learning.Outcome(
            group=str(o.donation_ref),
            features=o.features,
            accepted=o.accepted,
        )
        for o in offers
    ]
    evaluation = learning.evaluate(pool, bootstrap=0)
    assert evaluation.weights is not None
    assert evaluation.weights[ScoreFactor.PROXIMITY] > SCORE_WEIGHTS[ScoreFactor.PROXIMITY]
    assert evaluation.weights[ScoreFactor.PROXIMITY] == max(evaluation.weights.values())
    assert TRUE_MODEL.coefficients[ScoreFactor.PROXIMITY] > TRUE_MODEL.coefficients[ScoreFactor.NEED_MATCH]


def test_a_wider_offer_pool_changes_who_is_offered_and_spreads_the_factors():
    """With offer_pool 1 every offer goes to the top candidate; a wider pool models a donor
    who may choose any of the top few, so need match varies in the offered set."""
    generated = world.generate(8, orgs=40, donations=300)
    top_only = engine.run(generated, 8)
    wide = engine.run(generated, 8, offer_pool=8)
    assert top_only != wide
    need = learning.FACTORS.index(ScoreFactor.NEED_MATCH)

    def spread(offers):
        values = [o.features[need] for o in offers]
        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)

    assert spread(wide) > spread(top_only)


def test_the_wider_pool_still_goes_through_the_real_scoring_function(monkeypatch):
    calls = []
    real_rank = scoring_module.rank
    monkeypatch.setattr(scoring_module, "rank", lambda *a, **k: calls.append(1) or real_rank(*a, **k))
    engine.run(world.generate(9, orgs=10, donations=10), 9, offer_pool=5)
    assert calls


def test_outcomes_are_identical_across_separate_processes_with_different_hash_seeds():
    """Python randomises string hashing per process, so anything that depends on set order
    changes between runs. Running in-process twice cannot catch that; separate processes can."""
    import os
    import subprocess
    import sys

    code = """
import hashlib
from sim import engine, world
offers = engine.run(world.generate(5, orgs=20, donations=150), 5, offer_pool=4)
rows = [(o.donation_ref, o.organization_ref, o.features, o.accepted) for o in offers]
print(hashlib.sha256(repr(rows).encode()).hexdigest())
"""
    digests = set()
    for hash_seed in ("1", "2", "3"):
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, check=True, cwd=SIM_DIR.parent,
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
        )
        digests.add(result.stdout.strip())
    assert len(digests) == 1, "simulation output depends on the process's hash seed"
