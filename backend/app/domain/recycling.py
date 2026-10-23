"""Recycling fallback: choosing a recycler and computing the simulated settlement.

Pure. Mass is ESTIMATED (quantity x a per-category weight that is currently a
placeholder, see app.constants.CATEGORY_WEIGHT_KG) and the settlement is SIMULATED: no
money moves. Phase 4 will create wallet transactions from these records.
"""

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.constants import (
    CATEGORY_WEIGHT_KG,
    RECYCLER_MAX_RADIUS_KM,
    RECYCLING_PLATFORM_FEE_PCT,
    Category,
)
from app.domain.geo import haversine_km

_PAISE = Decimal("0.01")
_GRAMS = Decimal("0.001")


@dataclass(frozen=True)
class CollectorFacts:
    collector_id: uuid.UUID
    latitude: float
    longitude: float
    is_active: bool
    categories_accepted: frozenset[Category]


def select_recycler(
    category: Category,
    latitude: float,
    longitude: float,
    collectors: Iterable[CollectorFacts],
    max_radius_km: float = RECYCLER_MAX_RADIUS_KM,
) -> tuple[CollectorFacts, float] | None:
    """The nearest active collector that accepts the category within range, with its
    distance; None if there is none (the caller must surface that, never hide it)."""
    eligible = []
    for c in collectors:
        if not c.is_active or category not in c.categories_accepted:
            continue
        distance = haversine_km(latitude, longitude, c.latitude, c.longitude)
        if distance <= max_radius_km:
            eligible.append((distance, str(c.collector_id), c))
    if not eligible:
        return None
    distance, _, collector = min(eligible)
    return collector, round(distance, 3)


@dataclass(frozen=True)
class Settlement:
    weight_per_item_kg: Decimal
    estimated_mass_kg: Decimal
    rate_per_kg: Decimal
    gross_value: Decimal
    platform_fee_pct: Decimal
    platform_fee: Decimal
    donor_credit: Decimal


def settle(
    category: Category,
    quantity: int,
    rate_per_kg: Decimal,
    weights: Mapping[Category, Decimal] = CATEGORY_WEIGHT_KG,
    fee_pct: Decimal = RECYCLING_PLATFORM_FEE_PCT,
) -> Settlement:
    """gross = estimated mass x rate; the fee is a percentage of gross, rounded to the
    paisa; the donor is credited the rest, so credit + fee == gross exactly."""
    weight = weights[category]
    mass = (weight * quantity).quantize(_GRAMS, rounding=ROUND_HALF_UP)
    gross = (mass * rate_per_kg).quantize(_PAISE, rounding=ROUND_HALF_UP)
    fee = (gross * fee_pct / 100).quantize(_PAISE, rounding=ROUND_HALF_UP)
    return Settlement(
        weight_per_item_kg=weight,
        estimated_mass_kg=mass,
        rate_per_kg=rate_per_kg,
        gross_value=gross,
        platform_fee_pct=fee_pct,
        platform_fee=fee,
        donor_credit=gross - fee,
    )
