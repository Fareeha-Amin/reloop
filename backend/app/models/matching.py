import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import HandoverMode, OfferResponse, OfferSource, RankingTrigger, RejectReason
from app.db import AppendOnly, Base, StrEnumType, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.organization import OrganizationProfile
    from app.models.recycling import Recycling


class RankingRun(UUIDPrimaryKey, AppendOnly, Base):
    """One ranking of a donation that led to a decision (an offer, or an escalation for
    want of candidates), with its FULL eligible slate. Responses to top-ranked candidates
    alone would bias any later calibration, so the whole slate is kept.

    Previews the donor looks at are not stored: a read must not write, and the offer
    re-ranks and stores the slate it was actually made against."""

    __tablename__ = "ranking_runs"

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    trigger: Mapped[RankingTrigger] = mapped_column(StrEnumType(RankingTrigger))
    radius_km: Mapped[float] = mapped_column(Float)
    declines: Mapped[int] = mapped_column(Integer)
    config_version: Mapped[str] = mapped_column(String(32))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # [{rank, organization_id, organization_name, pickup_capable, distance_km, score,
    #   components: [{factor, raw, value, weight, contribution}]}]
    slate: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # {FilterReason: count} for organisations removed by the hard filters
    filtered_out: Mapped[dict[str, int]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Match(UUIDPrimaryKey, AppendOnly, Base):
    """One offer of one donation to one organisation. Never deleted, never overwritten.

    The response columns are NULL while the offer is open and are written exactly once
    (write-once from NULL is not overwriting; see app.db.AppendOnly)."""

    __tablename__ = "matches"
    __write_once__ = frozenset({"response", "reason_code", "note", "responder_id", "responded_at"})
    __table_args__ = (
        # An organisation is never offered the same donation twice: the exclusion list,
        # enforced by the database.
        UniqueConstraint("donation_id", "organization_id", name="uq_matches_donation_organization"),
        # At most one open offer per donation.
        Index(
            "uq_matches_one_open_offer_per_donation",
            "donation_id",
            unique=True,
            postgresql_where=text("response IS NULL"),
        ),
        Index("ix_matches_open_by_organization", "organization_id", postgresql_where=text("response IS NULL")),
        CheckConstraint("(response IS NULL) = (responded_at IS NULL)", name="response_has_time"),
        CheckConstraint("expires_at > offered_at", name="expiry_after_offer"),
        CheckConstraint("rank >= 1", name="rank_positive"),
    )

    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization_profiles.id"))
    # The candidate this offer was made to: (run, rank) points into ranking_runs.slate.
    ranking_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ranking_runs.id"))
    rank: Mapped[int] = mapped_column(Integer)
    offered_by: Mapped[OfferSource] = mapped_column(StrEnumType(OfferSource))
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    response: Mapped[OfferResponse | None] = mapped_column(StrEnumType(OfferResponse))
    reason_code: Mapped[RejectReason | None] = mapped_column(StrEnumType(RejectReason))
    note: Mapped[str | None] = mapped_column(Text)
    responder_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # NULL: the system
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["OrganizationProfile"] = relationship()
    ranking_run: Mapped[RankingRun] = relationship()
    handover: Mapped["Handover | None"] = relationship(back_populates="match")

    @property
    def is_open(self) -> bool:
        return self.response is None

    def respond(
        self,
        response: OfferResponse,
        at: datetime,
        responder_id: uuid.UUID | None = None,
        reason_code: RejectReason | None = None,
        note: str | None = None,
    ) -> None:
        if not self.is_open:
            raise ValueError("This offer already has a response.")
        self.response = response
        self.responded_at = at
        self.responder_id = responder_id
        self.reason_code = reason_code
        self.note = note


class Handover(UUIDPrimaryKey, AppendOnly, Base):
    """The agreed handover for an accepted offer, or (added for the recycling handover
    step) for a donation routed to a recycler. The mode decides who set the time;
    rescheduling is not supported yet (Phase 4 logistics).

    Exactly one of match_id / recycling_id is set — a handover is either to the
    organisation that accepted the donation, or to the recycler it was redirected to,
    never both. Enforced by a DB CHECK constraint (migration 0007): this protects an
    invariant across two nullable foreign keys, not a vocabulary value, so it is the
    one place a CHECK repeats a rule the app also enforces."""

    __tablename__ = "handovers"
    __table_args__ = (
        CheckConstraint(
            "(match_id IS NULL) != (recycling_id IS NULL)",
            name="handover_exactly_one_of_match_or_recycling",
        ),
    )

    match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("matches.id"), unique=True)
    recycling_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("recyclings.id"), unique=True)
    mode: Mapped[HandoverMode] = mapped_column(StrEnumType(HandoverMode))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arranged_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped["Match | None"] = relationship(back_populates="handover")
    recycling: Mapped["Recycling | None"] = relationship(back_populates="handover")
