"""The in-app notification feed: status events, organisation registrations and chat
messages, as seen by one user."""

import uuid
from datetime import datetime

from pydantic import Field

from app.constants import (
    Actor,
    Category,
    DonationAction,
    DonationStatus,
    EscalationCause,
    NotificationKind,
    VerificationStatus,
)
from app.schemas.common import OutputModel


def notification_key(kind: NotificationKind, source_id: object) -> str:
    """The one place a notification key is built: unique across kinds, and stable."""
    return f"{kind.value}:{source_id}"


class NotificationOut(OutputModel):
    """One feed item. Which fields are set depends on `kind`:

    - DONATION_EVENT: the donation fields and the transition (action, actor, states, cause);
      organization_name is the organisation of the offer the event concerns, if any.
    - ORGANISATION_REGISTERED (admins): organization_id, organization_name and the
      organisation's current verification_status.
    - CHAT_MESSAGE: the donation fields, and organization_name of the thread. Never the
      message text.

    Admin reasons, acceptors' rejection notes and chat text are never included."""

    kind: NotificationKind
    key: str = Field(description="Unique and stable; use it to remember which items have been read.")
    at: datetime
    donation_id: uuid.UUID | None = None
    category: Category | None = None
    quantity: int | None = Field(default=None, description="A count of items.")
    action: DonationAction | None = None
    actor: Actor | None = None
    from_state: DonationStatus | None = None
    to_state: DonationStatus | None = None
    cause: EscalationCause | None = None
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    verification_status: VerificationStatus | None = Field(
        default=None, description="ORGANISATION_REGISTERED only: the organisation's status now."
    )
