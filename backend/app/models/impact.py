import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import Category, ImpactOutcome
from app.db import AppendOnly, Base, StrEnumType, UUIDPrimaryKey


class ImpactRecord(UUIDPrimaryKey, AppendOnly, Base):
    """One finished donation's contribution to impact. Written once, in the transaction
    that moves the donation to COMPLETED or RECYCLED; never edited or deleted.

    The per-item factors are snapshotted from app.constants when the record is written,
    so later tuning of those constants never changes an existing record. All figures
    are ESTIMATES. Carbon is NULL for recycled donations (only reuse is credited)."""

    __tablename__ = "impact_records"

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), unique=True)
    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    # The organisation that reused the donation; NULL for recycling.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_profiles.id"), index=True
    )
    outcome: Mapped[ImpactOutcome] = mapped_column(StrEnumType(ImpactOutcome))
    category: Mapped[Category] = mapped_column(StrEnumType(Category))
    quantity: Mapped[int] = mapped_column(Integer)  # items diverted
    mass_kg_per_item: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    mass_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3))  # estimated
    carbon_kg_per_item: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))  # estimated
    carbon_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))  # estimated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
