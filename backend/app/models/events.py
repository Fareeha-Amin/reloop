import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import AddressAccess, Actor, DonationAction, DonationStatus, EscalationCause
from app.db import AppendOnly, Base, StrEnumType, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.matching import Match


class StatusEvent(AppendOnly, Base):
    """The audit log of lifecycle transitions: one row per transition, written in the
    same transaction as the status change, with the donation row locked.

    The key is a sequence, not a UUID: several transitions can share one transaction
    (REJECT, then REOFFER) and one timestamp, and the timeline needs their order. Events
    are never addressed by id through the API, so the id need not be unguessable."""

    __tablename__ = "status_events"
    __table_args__ = (Index("ix_status_events_donation_id_id", "donation_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"))
    from_state: Mapped[DonationStatus] = mapped_column(StrEnumType(DonationStatus))
    to_state: Mapped[DonationStatus] = mapped_column(StrEnumType(DonationStatus))
    action: Mapped[DonationAction] = mapped_column(StrEnumType(DonationAction))
    actor: Mapped[Actor] = mapped_column(StrEnumType(Actor))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # NULL for SYSTEM
    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"))
    cause: Mapped[EscalationCause | None] = mapped_column(StrEnumType(EscalationCause))
    # Required for admin actions. Shown to admins only.
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Declared so the unit of work inserts a new Match before the event that names it.
    match: Mapped["Match | None"] = relationship()


class AddressAccessEvent(UUIDPrimaryKey, AppendOnly, Base):
    """Who was given, or looked at, a donor's precise pickup address (non-negotiable 10).

    Written from exactly two places: release to the accepting organisation at ACCEPT,
    and an admin reading a donation's detail."""

    __tablename__ = "address_access_events"

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organization_profiles.id"))
    kind: Mapped[AddressAccess] = mapped_column(StrEnumType(AddressAccess))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
