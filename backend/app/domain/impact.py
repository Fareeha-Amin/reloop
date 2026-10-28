"""Impact records: what a finished donation counts toward (pure; no database).

Every figure here is an ESTIMATE (non-negotiable 8). Mass is quantity times a per-category
weight; carbon is quantity times a per-category factor, and is counted for reuse only.
Both per-item factors are placeholders until sourced (see app.constants).

Reuse and recovery are kept apart: a recycled donation adds to recycled mass and items,
never to reused items, and a recycled donation has no carbon figure.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.constants import (
    CARBON_FACTOR_KG_PER_ITEM,
    CATEGORY_WEIGHT_KG,
    Category,
    DonationStatus,
    ImpactOutcome,
)

S = DonationStatus

_GRAMS = Decimal("0.001")


def outcome_for(state: DonationStatus) -> ImpactOutcome | None:
    """The impact outcome a donation in `state` counts toward, or None if it is not an
    outcome. Lives beside the lifecycle's OUTCOME_STATES, which decide what is an outcome."""
    return {S.COMPLETED: ImpactOutcome.REUSED, S.RECYCLED: ImpactOutcome.RECYCLED}.get(state)


@dataclass(frozen=True)
class Estimate:
    mass_kg_per_item: Decimal
    mass_kg: Decimal
    carbon_kg_per_item: Decimal | None  # None for recycling: no carbon is credited
    carbon_kg: Decimal | None


def estimate(
    category: Category,
    quantity: int,
    outcome: ImpactOutcome,
    weights: Mapping[Category, Decimal] = CATEGORY_WEIGHT_KG,
    carbon: Mapping[Category, Decimal] = CARBON_FACTOR_KG_PER_ITEM,
) -> Estimate:
    """The per-item factors and totals for one donation, snapshotted onto its record so
    later changes to the constants never rewrite it."""
    mass_per_item = weights[category]
    mass = (mass_per_item * quantity).quantize(_GRAMS, rounding=ROUND_HALF_UP)
    if outcome != ImpactOutcome.REUSED:
        return Estimate(mass_per_item, mass, None, None)
    carbon_per_item = carbon[category]
    return Estimate(
        mass_per_item,
        mass,
        carbon_per_item,
        (carbon_per_item * quantity).quantize(_GRAMS, rounding=ROUND_HALF_UP),
    )


@dataclass(frozen=True)
class Contribution:
    """One record's share of a total: what it is, and how much it counts for."""

    outcome: ImpactOutcome
    quantity: int
    mass_kg: Decimal
    carbon_kg: Decimal | None


@dataclass(frozen=True)
class Totals:
    reused_donations: int
    reused_items: int
    reused_mass_kg: Decimal
    recycled_donations: int
    recycled_items: int
    recycled_mass_kg: Decimal
    carbon_avoided_kg: Decimal  # reuse only


def totals(contributions: Iterable[Contribution]) -> Totals:
    reused = [c for c in contributions if c.outcome == ImpactOutcome.REUSED]
    recycled = [c for c in contributions if c.outcome == ImpactOutcome.RECYCLED]
    zero = Decimal("0")
    return Totals(
        reused_donations=len(reused),
        reused_items=sum(c.quantity for c in reused),
        reused_mass_kg=sum((c.mass_kg for c in reused), zero),
        recycled_donations=len(recycled),
        recycled_items=sum(c.quantity for c in recycled),
        recycled_mass_kg=sum((c.mass_kg for c in recycled), zero),
        carbon_avoided_kg=sum((c.carbon_kg or zero for c in reused), zero),
    )
