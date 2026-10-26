import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import AppendOnly, Base, Timestamps, UUIDPrimaryKey


class LogisticsProvider(UUIDPrimaryKey, Timestamps, Base):
    """A SIMULATED courier. Fictional, seeded (python -m app.cli seed), same as
    WasteCollector: pricing lives on the record, not in code, so a real courier API
    can slot in later without touching callers."""

    __tablename__ = "logistics_providers"
    __table_args__ = (
        CheckConstraint("base_fee >= 0", name="base_fee_non_negative"),
        CheckConstraint("per_km_rate >= 0", name="per_km_rate_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(200), unique=True)
    base_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    per_km_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Booking(UUIDPrimaryKey, AppendOnly, Base):
    """A donor's platform-arranged pickup for one accepted offer. Status is derived from
    which of the nullable timestamps below are set, never stored as a column, so the
    whole row is append-only: booked_at is written once at insert, each other timestamp
    (and cancel_reason) is written at most once from NULL.

    picked_up_at and delivered_at are set as a side effect of the donor's
    MARK_HANDED_OVER and the acceptor's CONFIRM_RECEIPT (app.services.actions,
    app.services.offers) — booking status tracks the donation's handover, it does not
    replace it. cancelled_at is set when the donation stalls out of
    lifecycle.HELD_STATES without completing (app.services.sweeper), together with a
    full refund of its Payment (app.services.logistics.cancel_and_refund)."""

    __tablename__ = "bookings"
    __write_once__ = frozenset({"picked_up_at", "delivered_at", "cancelled_at", "cancel_reason"})
    __table_args__ = (
        CheckConstraint("cost = wallet_applied + gateway_amount", name="cost_splits_exactly"),
        CheckConstraint(
            "NOT (delivered_at IS NOT NULL AND cancelled_at IS NOT NULL)", name="not_both_delivered_and_cancelled"
        ),
        CheckConstraint("(cancelled_at IS NULL) = (cancel_reason IS NULL)", name="cancel_reason_with_cancellation"),
        CheckConstraint("distance_km >= 0", name="distance_non_negative"),
        CheckConstraint("cost >= 0 AND wallet_applied >= 0 AND gateway_amount >= 0", name="amounts_non_negative"),
    )

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    handover_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("handovers.id"), unique=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logistics_providers.id"))
    distance_km: Mapped[float] = mapped_column(Float)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    wallet_applied: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    gateway_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    arranged_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[LogisticsProvider] = relationship()
    # passive_deletes: nothing ever deletes a Booking (AppendOnly), but if it were
    # attempted, this must not first try to null out Payment.booking_id (itself
    # immutable) — Booking's own before_delete guard should refuse it directly.
    payment: Mapped["Payment | None"] = relationship(back_populates="booking", passive_deletes=True)


class Payment(UUIDPrimaryKey, AppendOnly, Base):
    """A SIMULATED Razorpay-style checkout: auto-succeeds at insert. amount is what the
    gateway charged (cost minus any wallet credit applied); refunded_at is set once, in
    the same transaction that cancels the booking, if the courier never delivered."""

    __tablename__ = "payments"
    __write_once__ = frozenset({"refunded_at", "refund_transaction_id"})
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint("(refunded_at IS NULL) = (refund_transaction_id IS NULL)", name="refund_has_transaction_id"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refund_transaction_id: Mapped[str | None] = mapped_column(String(64), unique=True)

    booking: Mapped[Booking] = relationship(back_populates="payment")
