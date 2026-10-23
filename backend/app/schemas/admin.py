import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.constants import Category, DonationAction, DonationStatus, RankingTrigger
from app.schemas.common import OutputModel
from app.schemas.donation import DonationOut, DonationSummaryOut
from app.schemas.timeline import TimelineOut


class QueueItemOut(OutputModel):
    """A donation in NEEDS_ADMIN, with the transition that put it there."""

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
    slate: list[dict[str, Any]]
    filtered_out: dict[str, int]
    created_at: datetime


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
    is_active: bool
