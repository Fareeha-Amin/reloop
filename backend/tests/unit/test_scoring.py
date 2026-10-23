import math
import uuid
from dataclasses import replace

import pytest

from app.constants import SCORE_WEIGHTS, Category, FilterReason, ScoreFactor, Urgency
from app.domain.geo import haversine_km
from app.domain.scoring import (
    DonationFacts,
    MatchingConfig,
    OrganisationFacts,
    acceptance_rate,
    hard_filter,
    rank,
    score_components,
)

CONFIG = MatchingConfig()
DONATION = DonationFacts(category=Category.CLOTHES, quantity=10, latitude=12.9784, longitude=77.6408)


def org(**overrides) -> OrganisationFacts:
    base = dict(
        organization_id=uuid.uuid4(),
        name="Org",
        latitude=12.9719,
        longitude=77.6412,
        verified=True,
        categories_accepted=frozenset({Category.CLOTHES}),
        pickup_capable=True,
        storage_capacity=100,
        held_quantity=0,
        need_urgency=None,
        need_quantity=None,
        accepted_offers=0,
        decided_offers=0,
    )
    base.update(overrides)
    return OrganisationFacts(**base)


def components(o: OrganisationFacts, distance=1.0, radius=15.0) -> dict[ScoreFactor, object]:
    return {c.factor: c for c in score_components(o, distance, radius, CONFIG)}


# --- Configuration ---------------------------------------------------------------------------


def test_weights_cover_every_factor_and_sum_to_one():
    assert set(SCORE_WEIGHTS) == set(ScoreFactor)
    assert math.isclose(sum(SCORE_WEIGHTS.values()), 1.0)


def test_config_rejects_weights_that_do_not_sum_to_one():
    with pytest.raises(ValueError):
        MatchingConfig(weights={f: 0.5 for f in ScoreFactor})


def test_config_version_is_stable_and_changes_with_config():
    assert MatchingConfig().version() == MatchingConfig().version()
    assert MatchingConfig(rejection_boost_enabled=False).version() != MatchingConfig().version()


# --- Hard filters ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "distance", "excluded", "reason"),
    [
        (dict(verified=False), 1.0, False, FilterReason.NOT_VERIFIED),
        (dict(categories_accepted=frozenset({Category.BOOKS})), 1.0, False, FilterReason.CATEGORY_NOT_ACCEPTED),
        ({}, 1.0, True, FilterReason.EXCLUDED),
        ({}, 15.01, False, FilterReason.OUT_OF_RADIUS),
        (dict(storage_capacity=100, held_quantity=91), 1.0, False, FilterReason.INSUFFICIENT_CAPACITY),
    ],
)
def test_each_hard_filter_excludes_on_its_own(overrides, distance, excluded, reason):
    o = org(**overrides)
    ex = frozenset({o.organization_id}) if excluded else frozenset()
    assert hard_filter(DONATION, o, distance, 15.0, ex) == reason


def test_eligible_organisation_passes_every_filter():
    o = org(storage_capacity=100, held_quantity=90)  # exactly enough room
    assert hard_filter(DONATION, o, 15.0, 15.0, frozenset()) is None


# --- Factors ---------------------------------------------------------------------------------


def test_every_factor_is_in_unit_interval_and_contributions_are_weighted():
    c = components(org(need_urgency=Urgency.HIGH, need_quantity=5, accepted_offers=3, decided_offers=7))
    for comp in c.values():
        assert 0.0 <= comp.value <= 1.0
        assert comp.contribution == pytest.approx(comp.weight * comp.value, abs=1e-6)


def test_proximity_is_one_at_zero_and_zero_at_the_radius():
    assert components(org(), distance=0.0)[ScoreFactor.PROXIMITY].value == 1.0
    assert components(org(), distance=15.0)[ScoreFactor.PROXIMITY].value == 0.0
    assert components(org(), distance=7.5)[ScoreFactor.PROXIMITY].value == pytest.approx(0.5)


def test_need_and_urgency():
    none = components(org())
    assert (none[ScoreFactor.NEED_MATCH].value, none[ScoreFactor.URGENCY].value) == (0.0, 0.0)
    assert none[ScoreFactor.URGENCY].raw is None
    for urgency, expected in [(Urgency.LOW, 0.33), (Urgency.MEDIUM, 0.67), (Urgency.HIGH, 1.0)]:
        c = components(org(need_urgency=urgency, need_quantity=20))
        assert c[ScoreFactor.NEED_MATCH].value == 1.0
        assert c[ScoreFactor.URGENCY].value == expected
        assert (c[ScoreFactor.URGENCY].raw, c[ScoreFactor.NEED_MATCH].raw) == (urgency.value, 20)


def test_capacity_headroom_and_clamping():
    assert components(org(storage_capacity=100, held_quantity=20))[ScoreFactor.CAPACITY_HEADROOM].value == 0.8
    # Over capacity (an organisation may accept beyond it): clamped, never negative.
    assert components(org(storage_capacity=100, held_quantity=150))[ScoreFactor.CAPACITY_HEADROOM].value == 0.0


def test_new_organisation_gets_the_neutral_prior():
    c = components(org())[ScoreFactor.ACCEPTANCE_RATE]
    assert c.value == CONFIG.acceptance_prior_rate
    assert c.raw is None


def test_acceptance_rate_is_smoothed_toward_the_prior():
    # 1 of 1 accepted: well above the prior, well below a perfect 1.0.
    assert acceptance_rate(1, 1, CONFIG) == pytest.approx((1 + 4 * 0.5) / 5)
    # A long perfect record approaches 1.
    assert acceptance_rate(100, 100, CONFIG) > 0.98
    assert acceptance_rate(0, 100, CONFIG) < 0.02


# --- Ranking ---------------------------------------------------------------------------------


def test_score_is_the_sum_of_contributions():
    slate = rank(DONATION, [org(need_urgency=Urgency.MEDIUM, need_quantity=3)], frozenset(), 15.0, CONFIG)
    c = slate.candidates[0]
    assert c.score == pytest.approx(sum(comp.contribution for comp in c.components), abs=1e-6)


def test_need_outranks_mere_proximity():
    """The motivating case: an organisation next door with no need and little room should
    not beat one a few km away that urgently needs exactly this."""
    near = org(name="Near", latitude=12.9790, longitude=77.6410, storage_capacity=100, held_quantity=85)
    needy = org(name="Needy", latitude=12.9352, longitude=77.6245, need_urgency=Urgency.HIGH, need_quantity=40)
    slate = rank(DONATION, [near, needy], frozenset(), 15.0, CONFIG)
    assert [c.organization_name for c in slate.candidates] == ["Needy", "Near"]


def test_ranks_are_dense_from_one_and_filtered_are_counted():
    eligible = [org(name=f"O{i}") for i in range(3)]
    unverified = org(verified=False)
    far = org(latitude=13.5, longitude=77.6)
    slate = rank(DONATION, [*eligible, unverified, far], frozenset(), 15.0, CONFIG)
    assert [c.rank for c in slate.candidates] == [1, 2, 3]
    assert dict(slate.filtered_out) == {FilterReason.NOT_VERIFIED: 1, FilterReason.OUT_OF_RADIUS: 1}


def test_ties_break_on_distance_then_id_deterministically():
    a = org(name="A", organization_id=uuid.UUID(int=2))
    b = org(name="B", organization_id=uuid.UUID(int=1))  # identical facts and location
    first = rank(DONATION, [a, b], frozenset(), 15.0, CONFIG)
    second = rank(DONATION, [b, a], frozenset(), 15.0, CONFIG)
    assert [c.organization_name for c in first.candidates] == ["B", "A"]
    assert first == second


def test_wider_radius_admits_farther_organisations():
    far = org(latitude=13.1155, longitude=77.5960)  # Yelahanka, ~16 km from Indiranagar
    d = haversine_km(DONATION.latitude, DONATION.longitude, far.latitude, far.longitude)
    assert 15 < d < 18.75
    assert rank(DONATION, [far], frozenset(), 15.0, CONFIG).is_empty
    assert not rank(DONATION, [far], frozenset(), 18.75, CONFIG).is_empty


def test_slate_helpers():
    a, b = org(name="A"), org(name="B", latitude=12.99)
    slate = rank(DONATION, [a, b], frozenset(), 15.0, CONFIG)
    assert slate.top().organization_name == "A"
    assert slate.find(b.organization_id).organization_name == "B"
    assert slate.find(uuid.uuid4()) is None
    assert replace(slate, candidates=()).top() is None
