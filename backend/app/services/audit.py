"""Address-access audit (non-negotiable 10). Deliberately minimal: one append-only table,
written from exactly two places — release to the accepting organisation (offers.accept)
and an admin reading a donation's detail (donations.read)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.constants import AddressAccess
from app.models import AddressAccessEvent, Donation, OrganizationProfile, User


def record_address_access(
    db: Session,
    donation: Donation,
    user: User,
    kind: AddressAccess,
    now: datetime,
    organization: OrganizationProfile | None = None,
) -> None:
    db.add(
        AddressAccessEvent(
            donation_id=donation.id,
            user_id=user.id,
            organization_id=organization.id if organization is not None else None,
            kind=kind,
            created_at=now,
        )
    )
