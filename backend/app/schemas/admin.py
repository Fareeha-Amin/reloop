import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.constants import (
    CURRENCY,
    Category,
    CommissionSource,
    DonationAction,
    DonationStatus,
    FilterReason,
    RankingTrigger,
)
from app.schemas.common import OutputModel
from app.schemas.donation import DonationOut, DonationSummaryOut
from app.schemas.matching import CandidateOut, ModelOut
from app.schemas.timeline import TimelineOut


class QueueItemOut(OutputModel):
    """A donation waiting on an admin, with the transition that put it there."""

    donation: DonationSummaryOut
    entered_at: datetime
    from_state: DonationStatus
    via: DonationAction
    allowed_actions: list[DonationAction]


class RankingRunOut(OutputModel):
    id: uuid.UUID
    trigger: RankingTrigger
    radius_km: float
    declines: int
    config_version: str
    config: dict[str, Any]
    slate: list[CandidateOut] = Field(description="The eligible organisations the decision was made against, best first.")
    filtered_out: dict[FilterReason, int]
    created_at: datetime
    model: ModelOut | None = Field(
        default=None,
        description="The weights this run used: the prior or a fit, with its training sample. Null only for a version no record exists for.",
    )


class AdminDonationDetailOut(OutputModel):
    """Includes the precise address; every read is recorded in address_access_events."""

    donation: DonationOut
    timeline: TimelineOut
    ranking_runs: list[RankingRunOut]


class SweepItemOut(OutputModel):
    donation_id: uuid.UUID
    from_state: DonationStatus
    action: DonationAction
    to_state: DonationStatus


class SweepReportOut(OutputModel):
    now: datetime
    examined: int
    skipped_locked: int
    applied: list[SweepItemOut]
    errors: list[str]


class RecyclerOut(OutputModel):
    id: uuid.UUID
    name: str
    address_text: str
    latitude: float
    longitude: float
    categories_accepted: list[Category]
    rate_per_kg: Decimal
    currency: str = CURRENCY
    is_active: bool


class CommissionEntryOut(OutputModel):
    """One ledger row. A cancelled, undelivered booking's commission is reversed by a
    second row with the negated amount (never edited or deleted)."""

    id: uuid.UUID
    source: CommissionSource
    source_id: uuid.UUID = Field(description="A Booking id (LOGISTICS) or a Recycling id (RECYCLING).")
    amount: Decimal
    note: str | None
    created_at: datetime


class CommissionSummaryOut(OutputModel):
    total: Decimal = Field(description="SUM(amount); net of any reversals.")
    currency: str = CURRENCY
    entries: list[CommissionEntryOut]
