import uuid
from datetime import UTC, datetime

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from app.constants import Category, Condition, DonationAction, DonationStatus, EscalationCause
from app.schemas.common import (
    Address,
    InputModel,
    ItemCount,
    Latitude,
    Longitude,
    Note,
    OutputModel,
    check_location_update,
    reject_explicit_nulls,
)
from app.domain import lifecycle


def validate_pickup_window(start: datetime, end: datetime, now: datetime | None = None) -> None:
    if end <= start:
        raise ValueError("pickup_window_end must be after pickup_window_start.")
    if end <= (now or datetime.now(UTC)):
        raise ValueError("pickup_window_end must be in the future.")


class DonationCreate(InputModel):
    # Shown pre-filled in /docs. The window must end in the future.
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "category": Category.CLOTHES.value,
                    "quantity": 12,
                    "condition": Condition.GENTLY_USED.value,
                    "note": "Children's winter clothes, ages 4-8",
                    "is_priority": False,
                    "pickup_address_text": "45 Indiranagar 100ft Rd, Bengaluru",
                    "pickup_latitude": 12.9784,
                    "pickup_longitude": 77.6408,
                    "pickup_window_start": "2030-01-15T10:00:00+05:30",
                    "pickup_window_end": "2030-01-15T13:00:00+05:30",
                }
            ]
        }
    )

    category: Category
    quantity: ItemCount
    condition: Condition
    note: Note | None = None
    is_priority: bool = False
    pickup_address_text: Address
    pickup_latitude: Latitude
    pickup_longitude: Longitude
    pickup_window_start: AwareDatetime
    pickup_window_end: AwareDatetime

    @model_validator(mode="after")
    def check_window(self):
        validate_pickup_window(self.pickup_window_start, self.pickup_window_end)
        return self


class DonationUpdate(InputModel):
    """Any subset of the donor-editable fields. Status is not here: it changes only
    through lifecycle actions such as POST /donations/{id}/cancel."""

    category: Category | None = None
    quantity: ItemCount | None = None
    condition: Condition | None = None
    note: Note | None = None
    is_priority: bool | None = None
    pickup_address_text: Address | None = None
    pickup_latitude: Latitude | None = None
    pickup_longitude: Longitude | None = None
    pickup_window_start: AwareDatetime | None = None
    pickup_window_end: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_partial_update(self):
        reject_explicit_nulls(self, clearable=frozenset({"note"}))
        check_location_update(
            self.pickup_address_text, self.pickup_latitude, self.pickup_longitude
        )
        return self


class DonationImageOut(OutputModel):
    id: uuid.UUID
    content_type: str
    size_bytes: int
    created_at: datetime


class DonationSummaryOut(OutputModel):
    """A donation without its precise address or coordinates (admin lists and queue)."""

    id: uuid.UUID
    donor_id: uuid.UUID
    category: Category
    quantity: int = Field(description="A count of items.")
    condition: Condition
    is_priority: bool
    pickup_window_start: datetime
    pickup_window_end: datetime
    status: DonationStatus
    created_at: datetime
    updated_at: datetime


class DonationOut(OutputModel):
    id: uuid.UUID
    donor_id: uuid.UUID
    category: Category
    quantity: int = Field(description="A count of items.")
    condition: Condition
    note: str | None
    is_priority: bool
    pickup_address_text: str
    pickup_latitude: float
    pickup_longitude: float
    pickup_window_start: datetime
    pickup_window_end: datetime
    status: DonationStatus
    # Why the system escalated it, when status is ESCALATED.
    escalation_cause: EscalationCause | None = None
    # Derived from the lifecycle table and the policy guards, for this viewer, so
    # clients render buttons from the API instead of re-implementing status rules.
    editable: bool
    allowed_actions: list[DonationAction]
    images: list[DonationImageOut]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_donation(
        cls,
        donation,
        allowed_actions: frozenset[DonationAction],
        escalation_cause: EscalationCause | None = None,
    ) -> "DonationOut":
        data = {name: getattr(donation, name) for name in cls.model_fields if hasattr(donation, name)}
        data["editable"] = lifecycle.is_editable(donation.status)
        data["allowed_actions"] = sorted(allowed_actions)
        data["escalation_cause"] = escalation_cause
        return cls.model_validate(data)
