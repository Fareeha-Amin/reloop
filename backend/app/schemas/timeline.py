"""A donation's history: status events, offers and their responses, recycling."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.constants import (
    CATEGORY_WEIGHTS_ARE_PLACEHOLDERS,
    CURRENCY,
    Actor,
    DonationAction,
    DonationStatus,
    EscalationCause,
    HandoverMode,
    OfferResponse,
    OfferSource,
    RejectReason,
)
from app.schemas.common import OutputModel


class EventOut(OutputModel):
    at: datetime
    from_state: DonationStatus
    to_state: DonationStatus
    action: DonationAction
    actor: Actor
    cause: EscalationCause | None
    reason: str | None = Field(description="Admin-recorded reason. Shown to admins only.")


class HandoverOut(OutputModel):
    mode: HandoverMode
    scheduled_for: datetime


class OfferHistoryOut(OutputModel):
    match_id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    rank: int = Field(description="The organisation's rank in the slate the offer was made from.")
    offered_by: OfferSource
    offered_at: datetime
    expires_at: datetime
    response: OfferResponse | None = Field(description="null while the offer is open.")
    reason_code: RejectReason | None
    note: str | None = Field(description="The acceptor's note on a rejection. Shown to admins only.")
    responded_at: datetime | None
    handover: HandoverOut | None


class SettlementOut(OutputModel):
    weight_per_item_kg: Decimal
    estimated_mass_kg: Decimal
    rate_per_kg: Decimal
    gross_value: Decimal
    platform_fee_pct: Decimal
    platform_fee: Decimal
    donor_credit: Decimal
    confirmed_at: datetime


class RecyclingOut(OutputModel):
    """SIMULATED settlement over ESTIMATED mass. No money moves; Phase 4 adds wallets."""

    collector_id: uuid.UUID
    collector_name: str
    distance_km: float
    rate_per_kg: Decimal
    assigned_at: datetime
    settlement: SettlementOut | None = Field(description="Set once the recycling is confirmed.")
    currency: str = CURRENCY
    simulated: Literal[True] = True
    mass_is_estimate: Literal[True] = True
    weights_are_placeholders: bool = Field(
        default=CATEGORY_WEIGHTS_ARE_PLACEHOLDERS,
        description="The per-category weights are placeholders pending a cited source.",
    )


class TimelineOut(OutputModel):
    events: list[EventOut]
    offers: list[OfferHistoryOut]
    recyclings: list[RecyclingOut]
