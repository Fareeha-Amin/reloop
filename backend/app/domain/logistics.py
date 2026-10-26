"""Platform-arranged pickup: pricing and the wallet/gateway split. Pure.

Cost is SIMULATED and distance-based (no real courier API). Mass and carbon are not
estimated here — this module only prices a booking and decides how much of it a
donor's wallet balance covers.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.constants import LOGISTICS_PLATFORM_FEE_PCT

_PAISE = Decimal("0.01")


def quote_cost(distance_km: float, base_fee: Decimal, per_km_rate: Decimal) -> Decimal:
    """base fee + per-km rate x distance, rounded to the paisa."""
    return (base_fee + per_km_rate * Decimal(str(distance_km))).quantize(_PAISE, rounding=ROUND_HALF_UP)


def commission_amount(cost: Decimal, fee_pct: Decimal = LOGISTICS_PLATFORM_FEE_PCT) -> Decimal:
    """The platform's cut of a booking's cost, same rounding as the recycling fee."""
    return (cost * fee_pct / 100).quantize(_PAISE, rounding=ROUND_HALF_UP)


def wallet_split(cost: Decimal, requested: Decimal, balance: Decimal) -> tuple[Decimal, Decimal]:
    """How much of `cost` the wallet covers: at most what was requested, at most the
    balance, at most the cost itself (never negative). The wallet is optional — a donor
    with no balance, or who requests none, pays the full cost through the gateway."""
    wallet_applied = max(Decimal("0"), min(requested, balance, cost))
    return wallet_applied, cost - wallet_applied
