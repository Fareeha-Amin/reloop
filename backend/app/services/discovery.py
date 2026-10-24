"""The public discovery map's read model."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.constants import Category, VerificationStatus
from app.models import OrganizationProfile


def verified_organisations(db: Session, category: Category | None) -> list[OrganizationProfile]:
    """Verified organisations, by name; only those accepting `category` if it is given."""
    query = (
        select(OrganizationProfile)
        .where(OrganizationProfile.verification_status == VerificationStatus.VERIFIED)
        .options(selectinload(OrganizationProfile.needs))
        .order_by(OrganizationProfile.name, OrganizationProfile.id)
    )
    if category is not None:
        query = query.where(OrganizationProfile.categories_accepted.contains([category]))
    return list(db.scalars(query))
