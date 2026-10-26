import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import CommissionSource, WalletTxnType
from app.db import AppendOnly, Base, StrEnumType, UUIDPrimaryKey


class WalletTxn(UUIDPrimaryKey, AppendOnly, Base):
    """A donor's append-only wallet ledger. The balance is SUM(amount), never stored.
    amount is signed: positive for a credit (a confirmed recycling, a refund), negative
    for a debit (wallet credit spent on a platform pickup). No withdrawals."""

    __tablename__ = "wallet_txns"
    __table_args__ = (
        CheckConstraint(
            "(reference_recycling_id IS NOT NULL) != (reference_booking_id IS NOT NULL)",
            name="exactly_one_reference",
        ),
    )

    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[WalletTxnType] = mapped_column(StrEnumType(WalletTxnType))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reference_recycling_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("recyclings.id"))
    reference_booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Commission(UUIDPrimaryKey, AppendOnly, Base):
    """The platform's earnings ledger, from logistics fees and recycling fees. Pure
    insert-only: a cancelled, undelivered booking's commission is reversed by a second
    row with the negated amount, never by editing or deleting the first."""

    __tablename__ = "commissions"

    source: Mapped[CommissionSource] = mapped_column(StrEnumType(CommissionSource))
    source_id: Mapped[uuid.UUID] = mapped_column(index=True)  # a Booking or Recycling id
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
