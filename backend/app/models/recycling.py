import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import Category
from app.db import AppendOnly, Base, StrEnumType, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.matching import Handover


class WasteCollector(UUIDPrimaryKey, Timestamps, Base):
    """A recycling partner. Its rate lives on this record, not in code; each recycling
    copies the rate it was assigned at, so later rate changes do not rewrite history."""

    __tablename__ = "waste_collectors"
    __table_args__ = (
        CheckConstraint("rate_per_kg >= 0", name="rate_non_negative"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
    )

    name: Mapped[str] = mapped_column(String(200), unique=True)
    address_text: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    categories_accepted: Mapped[list[Category]] = mapped_column(ARRAY(StrEnumType(Category)))
    rate_per_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # INR per kg of material
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Recycling(UUIDPrimaryKey, AppendOnly, Base):
    """A donation routed to a recycler, and (once confirmed) its SIMULATED settlement.

    Assignment columns are written at redirect. Settlement columns are NULL until the
    recycling is confirmed, then written once. Mass is ESTIMATED from the item count and
    a placeholder per-category weight. No money moves; Phase 4 creates wallet
    transactions from confirmed rows.

    A donation can have several rows if a recycling stalls and is redirected again; at
    most one is ever confirmed."""

    __tablename__ = "recyclings"
    __write_once__ = frozenset(
        {
            "weight_per_item_kg",
            "estimated_mass_kg",
            "gross_value",
            "platform_fee_pct",
            "platform_fee",
            "donor_credit",
            "confirmed_at",
            "confirmed_by_id",
        }
    )
    __table_args__ = (
        Index(
            "uq_recyclings_one_confirmed_per_donation",
            "donation_id",
            unique=True,
            postgresql_where=text("confirmed_at IS NOT NULL"),
        ),
        CheckConstraint("(confirmed_at IS NULL) = (gross_value IS NULL)", name="settled_when_confirmed"),
    )

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    collector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("waste_collectors.id"))
    distance_km: Mapped[float] = mapped_column(Float)
    rate_per_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # copied from the collector
    assigned_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))  # donor or admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    weight_per_item_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    estimated_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    gross_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    platform_fee_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    platform_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    donor_credit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    collector: Mapped[WasteCollector] = relationship()
    # The donor's handover to this collector (drop-off or a simulated platform pickup),
    # if the donor has recorded one yet. passive_deletes: nothing ever deletes a
    # Recycling row (AppendOnly); if it were attempted, Handover's own before_delete
    # guard should refuse it directly rather than this relationship nulling it out.
    handover: Mapped["Handover | None"] = relationship(back_populates="recycling", passive_deletes=True)
