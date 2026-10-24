"""The in-app notification feed: status events, as seen by one user."""

import uuid
from datetime import datetime

from pydantic import Field

from app.constants import Actor, Category, DonationAction, DonationStatus, EscalationCause
from app.schemas.common import OutputModel


class NotificationOut(OutputModel):
    """One status event. Admin reasons and acceptors' rejection notes are never included;
    they stay in the admin detail view."""

    id: int = Field(description="The status event's id. Increases over time; use it to track what has been seen.")
    at: datetime
    donation_id: uuid.UUID
    category: Category
    quantity: int = Field(description="A count of items.")
    action: DonationAction
    actor: Actor
    from_state: DonationStatus
    to_state: DonationStatus
    cause: EscalationCause | None
    organization_name: str | None = Field(
        description="The organisation of the offer this event concerns, if any."
    )
