"""Platform-pickup pricing and the wallet/gateway split. Pure, Decimal arithmetic."""

from decimal import Decimal

import pytest

from app.domain.logistics import commission_amount, quote_cost, wallet_split


def test_quote_cost_is_base_fee_plus_distance_times_rate():
    cost = quote_cost(10.0, Decimal("40.00"), Decimal("12.00"))
    assert cost == Decimal("160.00")


def test_quote_cost_rounds_to_the_paisa_half_up():
    cost = quote_cost(3.333, Decimal("10.00"), Decimal("1.005"))
    assert cost == Decimal("13.35")  # 10 + 3.333*1.005 = 13.3496... -> half-up to 13.35


def test_commission_is_a_percentage_of_cost():
    assert commission_amount(Decimal("100.00"), Decimal("10")) == Decimal("10.00")
    assert commission_amount(Decimal("99.99"), Decimal("8")) == Decimal("8.00")  # 7.9992 -> 8.00


@pytest.mark.parametrize(
    ("cost", "requested", "balance", "wallet_applied", "gateway"),
    [
        # A zero balance is not an error: the wallet is optional. Full gateway payment.
        (Decimal("100.00"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("100.00")),
        (Decimal("100.00"), Decimal("50"), Decimal("0"), Decimal("0"), Decimal("100.00")),
        # Full coverage.
        (Decimal("100.00"), Decimal("100"), Decimal("250"), Decimal("100.00"), Decimal("0")),
        # Partial, by request, even though the balance could cover more.
        (Decimal("100.00"), Decimal("30"), Decimal("250"), Decimal("30.00"), Decimal("70.00")),
        # Requested more than the balance: capped at the balance.
        (Decimal("100.00"), Decimal("250"), Decimal("40"), Decimal("40.00"), Decimal("60.00")),
        # Requested more than the cost itself: capped at the cost (no overpayment).
        (Decimal("100.00"), Decimal("500"), Decimal("500"), Decimal("100.00"), Decimal("0")),
    ],
)
def test_wallet_split(cost, requested, balance, wallet_applied, gateway):
    applied, gateway_amount = wallet_split(cost, requested, balance)
    assert applied == wallet_applied
    assert gateway_amount == gateway
    assert applied + gateway_amount == cost


def test_wallet_split_never_goes_negative():
    applied, gateway_amount = wallet_split(Decimal("50.00"), Decimal("-10"), Decimal("-5"))
    assert applied == Decimal("0") and gateway_amount == Decimal("50.00")
