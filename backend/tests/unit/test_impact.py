"""Impact records are pure: estimates, the outcome mapping and the totals rollup. Every
figure they produce is an estimate, and reuse and recycling never count toward each other."""

from decimal import Decimal

from app.constants import (
    CARBON_FACTOR_KG_PER_ITEM,
    CATEGORY_WEIGHT_KG,
    CATEGORY_WEIGHTS_ARE_PLACEHOLDERS,
    Category,
    DonationStatus,
    ImpactOutcome,
)
from app.domain import impact
from app.domain.lifecycle import OUTCOME_STATES

S = DonationStatus


def test_outcome_states_map_to_their_impact_outcome_and_nothing_else_does():
    assert impact.outcome_for(S.COMPLETED) is ImpactOutcome.REUSED
    assert impact.outcome_for(S.RECYCLED) is ImpactOutcome.RECYCLED
    assert {impact.outcome_for(s) is not None for s in OUTCOME_STATES} == {True}
    for state in set(DonationStatus) - OUTCOME_STATES:
        assert impact.outcome_for(state) is None, state


def test_reuse_is_estimated_in_mass_and_carbon_per_item_times_quantity():
    est = impact.estimate(Category.CLOTHES, 4, ImpactOutcome.REUSED)
    assert est.mass_kg_per_item == CATEGORY_WEIGHT_KG[Category.CLOTHES]
    assert est.mass_kg == CATEGORY_WEIGHT_KG[Category.CLOTHES] * 4
    assert est.carbon_kg_per_item == CARBON_FACTOR_KG_PER_ITEM[Category.CLOTHES]
    assert est.carbon_kg == CARBON_FACTOR_KG_PER_ITEM[Category.CLOTHES] * 4


def test_recycling_is_credited_with_mass_only():
    est = impact.estimate(Category.BOOKS, 3, ImpactOutcome.RECYCLED)
    assert est.mass_kg == CATEGORY_WEIGHT_KG[Category.BOOKS] * 3
    assert est.carbon_kg is None and est.carbon_kg_per_item is None


def test_the_estimate_uses_the_factors_it_is_given():
    """The record snapshots the factors it was written with: a later constant change is
    never applied to an existing record, because nothing recomputes one."""
    weights = {c: Decimal("1") for c in Category}
    carbon = {c: Decimal("2") for c in Category}
    est = impact.estimate(Category.TOYS, 5, ImpactOutcome.REUSED, weights=weights, carbon=carbon)
    assert (est.mass_kg, est.carbon_kg) == (Decimal("5"), Decimal("10"))


def test_totals_keep_reuse_and_recycling_apart_and_count_carbon_for_reuse_only():
    contributions = [
        impact.Contribution(ImpactOutcome.REUSED, 4, Decimal("2.0"), Decimal("20.0")),
        impact.Contribution(ImpactOutcome.REUSED, 1, Decimal("0.5"), Decimal("5.0")),
        impact.Contribution(ImpactOutcome.RECYCLED, 3, Decimal("1.2"), None),
    ]
    t = impact.totals(contributions)
    assert (t.reused_donations, t.reused_items, t.reused_mass_kg) == (2, 5, Decimal("2.5"))
    assert (t.recycled_donations, t.recycled_items, t.recycled_mass_kg) == (1, 3, Decimal("1.2"))
    assert t.carbon_avoided_kg == Decimal("25.0")


def test_totals_of_nothing_are_zero():
    t = impact.totals([])
    assert t.reused_items == t.recycled_items == 0
    assert t.reused_mass_kg == t.recycled_mass_kg == t.carbon_avoided_kg == 0


def test_every_impact_factor_is_declared_for_every_category_and_flagged_as_placeholder():
    assert set(CARBON_FACTOR_KG_PER_ITEM) == set(Category)
    assert all(v > 0 for v in CARBON_FACTOR_KG_PER_ITEM.values())
    # Unsourced figures are labelled everywhere they appear (non-negotiable 8).
    assert CATEGORY_WEIGHTS_ARE_PLACEHOLDERS is True
