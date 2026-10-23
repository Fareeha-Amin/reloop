import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import Category, Condition, DonationStatus
from app.db import Base, StrEnumType, Timestamps, UUIDPrimaryKey
from app.domain.lifecycle import INITIAL_STATE


class Donation(UUIDPrimaryKey, Timestamps, Base):
    """A donor's listing. Never hard-deleted; a withdrawal moves it to CANCELLED.

    The pickup address and coordinates are sensitive (non-negotiable 10): the full row
    is readable by its donor and by admins (admin reads are recorded); an acceptor sees
    the address only while it holds the donation (see app.services.offers).

    The pickup window is advisory: acceptors see it, but nothing enforces it. A LISTED
    donation the donor never offers escalates after LISTED_STALL.

    Nothing about matching is stored here: offers, declines, exclusions and escalations
    are all derived from Match rows and StatusEvents.
    """

    __tablename__ = "donations"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="quantity_positive"),
        CheckConstraint("pickup_latitude BETWEEN -90 AND 90", name="pickup_latitude_range"),
        CheckConstraint("pickup_longitude BETWEEN -180 AND 180", name="pickup_longitude_range"),
        CheckConstraint("pickup_window_end > pickup_window_start", name="pickup_window_order"),
    )

    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[Category] = mapped_column(StrEnumType(Category))
    # A count of items.
    quantity: Mapped[int] = mapped_column(Integer)
    condition: Mapped[Condition] = mapped_column(StrEnumType(Condition))
    note: Mapped[str | None] = mapped_column(Text)
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    pickup_address_text: Mapped[str] = mapped_column(String(300))
    pickup_latitude: Mapped[float] = mapped_column(Float)
    pickup_longitude: Mapped[float] = mapped_column(Float)
    pickup_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Changed only through app.domain.lifecycle.
    status: Mapped[DonationStatus] = mapped_column(
        StrEnumType(DonationStatus),
        default=INITIAL_STATE,
        server_default=INITIAL_STATE.value,
        index=True,
    )

    images: Mapped[list["DonationImage"]] = relationship(
        back_populates="donation", order_by="DonationImage.created_at"
    )


class DonationImage(UUIDPrimaryKey, Base):
    """Metadata for one stored image. The bytes live behind app.services.storage under a
    random, non-guessable key and are served only through an authorised endpoint."""

    __tablename__ = "donation_images"

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(128), unique=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    donation: Mapped[Donation] = relationship(back_populates="images")
