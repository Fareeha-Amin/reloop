import uuid
from decimal import Decimal

import pytest

from app.constants import (
    CATEGORY_WEIGHT_KG,
    CATEGORY_WEIGHTS_ARE_PLACEHOLDERS,
    RECYCLING_PLATFORM_FEE_PCT,
    Category,
)
from app.domain.geo import (
    approximate_position,
    approximation_error_km,
    disclose_distance_km,
    haversine_km,
)
from app.domain.recycling import CollectorFacts, select_recycler, settle

INDIRANAGAR = (12.9784, 77.6408)


def collector(lat, lng, categories=(Category.CLOTHES,), active=True) -> CollectorFacts:
    return CollectorFacts(uuid.uuid4(), lat, lng, active, frozenset(categories))


# --- Geo ------------------------------------------------------------------------------------------


def test_haversine_known_distance():
    # MG Road to Indiranagar 100ft Road: about 5 km.
    assert haversine_km(12.9716, 77.5946, *INDIRANAGAR) == pytest.approx(5.07, abs=0.05)
    assert haversine_km(*INDIRANAGAR, *INDIRANAGAR) == 0.0


@pytest.mark.parametrize(
    ("exact", "shown"),
    [(0.0, 0.5), (0.1, 0.5), (0.74, 0.5), (0.76, 1.0), (1.25, 1.5), (2.2, 2.0), (2.3, 2.5), (14.9, 15.0)],
)
def test_disclosed_distance_is_rounded_to_half_km_and_never_zero(exact, shown):
    assert disclose_distance_km(exact) == shown


# --- Recycler selection ------------------------------------------------------------------------


def test_nearest_active_collector_accepting_the_category():
    near = collector(12.98, 77.64)
    farther = collector(13.03, 77.52)
    found = select_recycler(Category.CLOTHES, *INDIRANAGAR, [farther, near])
    assert found[0] == near and found[1] < 1


def test_inactive_wrong_category_and_out_of_range_are_skipped():
    candidates = [
        collector(12.98, 77.64, active=False),
        collector(12.98, 77.64, categories=(Category.BOOKS,)),
        collector(13.5, 77.6),  # ~58 km
    ]
    assert select_recycler(Category.CLOTHES, *INDIRANAGAR, candidates) is None


def test_no_collector_accepts_toys_gives_none():
    assert select_recycler(Category.TOYS, *INDIRANAGAR, [collector(12.98, 77.64)]) is None


# --- Settlement -----------------------------------------------------------------------------------


def test_settlement_arithmetic():
    s = settle(Category.CLOTHES, 12, Decimal("12.00"))
    assert s.weight_per_item_kg == CATEGORY_WEIGHT_KG[Category.CLOTHES]
    assert s.estimated_mass_kg == Decimal("6.000")
    assert s.gross_value == Decimal("72.00")
    assert s.platform_fee_pct == RECYCLING_PLATFORM_FEE_PCT
    assert s.platform_fee == Decimal("7.20")
    assert s.donor_credit == Decimal("64.80")


@pytest.mark.parametrize("quantity", [1, 3, 7, 11, 999])
@pytest.mark.parametrize("rate", [Decimal("8.50"), Decimal("12.00"), Decimal("0.33")])
def test_credit_plus_fee_is_exactly_gross(quantity, rate):
    for category in Category:
        s = settle(category, quantity, rate)
        assert s.donor_credit + s.platform_fee == s.gross_value
        assert s.gross_value == s.gross_value.quantize(Decimal("0.01"))


def test_weights_are_labelled_as_placeholders():
    assert CATEGORY_WEIGHTS_ARE_PLACEHOLDERS is True
    assert set(CATEGORY_WEIGHT_KG) == set(Category)


def test_approximate_position_rounds_to_two_decimals_by_default():
    assert approximate_position(12.97194, 77.64126) == (12.97, 77.64)
    assert approximate_position(12.97194, 77.64126, decimals=1) == (13.0, 77.6)


def test_approximate_position_stays_within_the_stated_error():
    error = approximation_error_km()
    assert 0.7 < error < 0.8  # two decimals: "about a kilometre"
    for lat, lng in [(12.97194, 77.64126), (12.975, 77.645), (0.004999, 0.004999), (-33.86785, 151.20732)]:
        assert haversine_km(lat, lng, *approximate_position(lat, lng)) <= error
