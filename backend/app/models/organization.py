import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import Category, Urgency, VerificationStatus
from app.db import Base, StrEnumType, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.user import User


class OrganizationProfile(UUIDPrimaryKey, Timestamps, Base):
    """An acceptor organisation. One login per organisation: user_id is unique."""

    __tablename__ = "organization_profiles"
    __table_args__ = (
        CheckConstraint("storage_capacity >= 0", name="storage_capacity_non_negative"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    # name and registration_id are fixed after registration (no rename after verification).
    name: Mapped[str] = mapped_column(String(200))
    registration_id: Mapped[str] = mapped_column(String(64), unique=True)
    contact_person: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(32))
    address_text: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    pickup_capable: Mapped[bool] = mapped_column(Boolean)
    # A count of items, not a mass or volume. Nothing decrements it yet.
    storage_capacity: Mapped[int] = mapped_column(Integer)
    categories_accepted: Mapped[list[Category]] = mapped_column(ARRAY(StrEnumType(Category)))

    verification_status: Mapped[VerificationStatus] = mapped_column(
        StrEnumType(VerificationStatus),
        default=VerificationStatus.PENDING,
        server_default=VerificationStatus.PENDING.value,
    )
    verification_note: Mapped[str | None] = mapped_column(Text)
    # Who last changed verification_status, and when. Only an admin can.
    verification_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_updated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="organization", foreign_keys=[user_id])
    needs: Mapped[list["CurrentNeed"]] = relationship(
        back_populates="organization", order_by="CurrentNeed.created_at"
    )


class CurrentNeed(UUIDPrimaryKey, Timestamps, Base):
    """One line of an organisation's needs list.

    Needs are never hard-deleted, only deactivated: the history of what was asked for is
    the input to demand forecasting (Phase 5). At most one ACTIVE need per
    (organisation, category), so the need-match factor in scoring is never ambiguous.
    """

    __tablename__ = "current_needs"
    __table_args__ = (
        CheckConstraint("quantity_needed >= 1", name="quantity_needed_positive"),
        Index(
            "uq_current_needs_one_active_per_category",
            "organization_id",
            "category",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organization_profiles.id"), index=True
    )
    category: Mapped[Category] = mapped_column(StrEnumType(Category))
    # A count of items.
    quantity_needed: Mapped[int] = mapped_column(Integer)
    urgency: Mapped[Urgency] = mapped_column(StrEnumType(Urgency))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    organization: Mapped[OrganizationProfile] = relationship(back_populates="needs")
