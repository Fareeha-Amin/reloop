import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field

from app.constants import CURRENCY, BookingStatus, PaymentStatus
from app.schemas.common import InputModel, OutputModel


class ProviderQuoteOut(OutputModel):
    provider_id: uuid.UUID
    provider_name: str
    cost: Decimal


class PickupQuoteOut(OutputModel):
    """A preview: nothing is stored. Booking re-quotes and stores what it quoted."""

    distance_km: float
    wallet_balance: Decimal
    currency: str = CURRENCY
    providers: list[ProviderQuoteOut]
    simulated: Literal[True] = True


class BookPickupIn(InputModel):
    provider_id: uuid.UUID
    scheduled_for: AwareDatetime
    wallet_amount: Decimal = Field(
        default=Decimal("0"), ge=0, description="How much of the wallet balance to apply; capped at the cost."
    )


class PaymentOut(OutputModel):
    amount: Decimal = Field(description="What the simulated gateway charged (cost minus wallet_applied).")
    transaction_id: str
    paid_at: datetime
    refunded_at: datetime | None
    refund_transaction_id: str | None
    status: PaymentStatus

    @classmethod
    def from_payment(cls, p) -> "PaymentOut":
        return cls(
            amount=p.amount,
            transaction_id=p.transaction_id,
            paid_at=p.paid_at,
            refunded_at=p.refunded_at,
            refund_transaction_id=p.refund_transaction_id,
            status=PaymentStatus.REFUNDED if p.refunded_at else PaymentStatus.SUCCEEDED,
        )


class BookingOut(OutputModel):
    """SIMULATED: no real courier, no real payment gateway. Status is derived from
    which of booked_at/picked_up_at/delivered_at/cancelled_at are set."""

    id: uuid.UUID
    provider_name: str
    distance_km: float
    cost: Decimal
    wallet_applied: Decimal
    gateway_amount: Decimal
    currency: str = CURRENCY
    status: BookingStatus
    booked_at: datetime
    picked_up_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    payment: PaymentOut
    simulated: Literal[True] = True

    @classmethod
    def from_booking(cls, b) -> "BookingOut":
        if b.cancelled_at is not None:
            status = BookingStatus.CANCELLED
        elif b.delivered_at is not None:
            status = BookingStatus.DELIVERED
        elif b.picked_up_at is not None:
            status = BookingStatus.PICKED_UP
        else:
            status = BookingStatus.BOOKED
        return cls(
            id=b.id,
            provider_name=b.provider.name,
            distance_km=b.distance_km,
            cost=b.cost,
            wallet_applied=b.wallet_applied,
            gateway_amount=b.gateway_amount,
            status=status,
            booked_at=b.booked_at,
            picked_up_at=b.picked_up_at,
            delivered_at=b.delivered_at,
            cancelled_at=b.cancelled_at,
            cancel_reason=b.cancel_reason,
            payment=PaymentOut.from_payment(b.payment),
        )
