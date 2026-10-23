"""What an acceptor sees. Before acceptance: no address and no coordinates, only a
distance rounded to DISTANCE_DISCLOSURE_STEP_KM."""

import uuid
from datetime import datetime

from pydantic import Field

from app.constants import (
    Category,
    Condition,
    DonationAction,
    DonationStatus,
    OfferResponse,
    RejectReason,
)
from app.schemas.common import OutputModel
from app.schemas.timeline import HandoverOut


class OfferOut(OutputModel):
    match_id: uuid.UUID
    donation_id: uuid.UUID
    category: Category
    quantity: int = Field(description="A count of items.")
    condition: Condition
    note: str | None
    is_priority: bool
    distance_km: float = Field(description="Approximate: rounded to the nearest 0.5 km.")
    pickup_window_start: datetime
    pickup_window_end: datetime
    image_ids: list[uuid.UUID] = Field(description="Fetch with GET /donations/{donation_id}/images/{image_id}.")
    offered_at: datetime
    expires_at: datetime
    response: OfferResponse | None
    reason_code: RejectReason | None
    allowed_actions: list[DonationAction]

    @classmethod
    def build(cls, view) -> "OfferOut":
        m, d = view.match, view.donation
        return cls(
            match_id=m.id,
            donation_id=d.id,
            category=d.category,
            quantity=d.quantity,
            condition=d.condition,
            note=d.note,
            is_priority=d.is_priority,
            distance_km=view.distance_km,
            pickup_window_start=d.pickup_window_start,
            pickup_window_end=d.pickup_window_end,
            image_ids=[i.id for i in d.images],
            offered_at=m.offered_at,
            expires_at=m.expires_at,
            response=m.response,
            reason_code=m.reason_code,
            allowed_actions=sorted(view.allowed_actions),
        )


class AcceptedDonationOut(OutputModel):
    """A donation this organisation accepted. The precise address is present only while
    the organisation holds it (ACCEPTED, PICKUP_SCHEDULED, IN_TRANSIT)."""

    donation_id: uuid.UUID
    match_id: uuid.UUID
    status: DonationStatus
    category: Category
    quantity: int = Field(description="A count of items.")
    condition: Condition
    note: str | None
    pickup_window_start: datetime
    pickup_window_end: datetime
    distance_km: float = Field(description="Approximate: rounded to the nearest 0.5 km.")
    address_released: bool
    pickup_address_text: str | None
    pickup_latitude: float | None
    pickup_longitude: float | None
    image_ids: list[uuid.UUID]
    handover: HandoverOut | None
    allowed_actions: list[DonationAction]

    @classmethod
    def build(cls, view, allowed_actions: frozenset[DonationAction]) -> "AcceptedDonationOut":
        d, m = view.donation, view.match
        released = view.address_released
        return cls(
            donation_id=d.id,
            match_id=m.id,
            status=d.status,
            category=d.category,
            quantity=d.quantity,
            condition=d.condition,
            note=d.note,
            pickup_window_start=d.pickup_window_start,
            pickup_window_end=d.pickup_window_end,
            distance_km=view.distance_km,
            address_released=released,
            pickup_address_text=d.pickup_address_text if released else None,
            pickup_latitude=d.pickup_latitude if released else None,
            pickup_longitude=d.pickup_longitude if released else None,
            image_ids=[i.id for i in d.images],
            handover=HandoverOut.model_validate(m.handover) if m.handover else None,
            allowed_actions=sorted(allowed_actions) if released else [],
        )
