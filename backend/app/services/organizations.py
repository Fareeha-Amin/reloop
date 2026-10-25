import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import VerificationStatus
from app.models import CurrentNeed, OrganizationProfile, User
from app.schemas.need import NeedCreate, NeedUpdate
from app.schemas.organization import OrganizationUpdate, VerificationUpdate
from app.services.errors import Conflict, NotFound
from app.services.geocoding import Geocoder


def get_for_user(db: Session, user: User) -> OrganizationProfile:
    org = db.scalar(select(OrganizationProfile).where(OrganizationProfile.user_id == user.id))
    if org is None:
        # Every acceptor is created with a profile, so this indicates a data problem.
        raise NotFound("No organisation profile exists for this account.")
    return org


def _active_need_categories(org: OrganizationProfile) -> set:
    return {need.category for need in org.needs if need.is_active}


def update_profile(
    db: Session, org: OrganizationProfile, data: OrganizationUpdate, geocoder: Geocoder
) -> OrganizationProfile:
    changes = data.model_dump(exclude_unset=True)

    if "categories_accepted" in changes:
        dropped = _active_need_categories(org) - set(changes["categories_accepted"])
        if dropped:
            names = ", ".join(sorted(dropped))
            raise Conflict(
                f"Active needs exist for {names}. Deactivate them before removing the category."
            )

    # The schema guarantees an address change always comes with new coordinates.
    if "latitude" in changes:
        location = geocoder.resolve(
            changes.get("address_text", org.address_text),
            changes["latitude"],
            changes["longitude"],
        )
        changes["address_text"] = location.address_text
        changes["latitude"] = location.latitude
        changes["longitude"] = location.longitude

    for field, value in changes.items():
        setattr(org, field, value)
    db.commit()
    return org


# --- Needs list -------------------------------------------------------------------------


def list_needs(db: Session, org: OrganizationProfile, active_only: bool) -> list[CurrentNeed]:
    query = select(CurrentNeed).where(CurrentNeed.organization_id == org.id)
    if active_only:
        query = query.where(CurrentNeed.is_active.is_(True))
    return list(db.scalars(query.order_by(CurrentNeed.created_at)))


def _ensure_no_other_active_need(db: Session, org: OrganizationProfile, category, exclude_id=None):
    query = select(CurrentNeed.id).where(
        CurrentNeed.organization_id == org.id,
        CurrentNeed.category == category,
        CurrentNeed.is_active.is_(True),
    )
    if exclude_id is not None:
        query = query.where(CurrentNeed.id != exclude_id)
    if db.scalar(query) is not None:
        raise Conflict(
            f"There is already an active need for {category}. Update it instead, or deactivate it first."
        )


def create_need(db: Session, org: OrganizationProfile, data: NeedCreate) -> CurrentNeed:
    if data.category not in org.categories_accepted:
        raise Conflict(f"This organisation does not accept {data.category}.")
    _ensure_no_other_active_need(db, org, data.category)
    need = CurrentNeed(
        organization_id=org.id,
        category=data.category,
        quantity_needed=data.quantity_needed,
        urgency=data.urgency,
        is_active=True,
    )
    db.add(need)
    db.commit()
    return need


def update_need(
    db: Session, org: OrganizationProfile, need_id: uuid.UUID, data: NeedUpdate
) -> CurrentNeed:
    need = db.get(CurrentNeed, need_id, with_for_update=True)
    if need is None or need.organization_id != org.id:
        raise NotFound("Need not found.")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_active") and not need.is_active:
        if need.category not in org.categories_accepted:
            raise Conflict(f"This organisation no longer accepts {need.category}.")
        _ensure_no_other_active_need(db, org, need.category, exclude_id=need.id)
    for field, value in changes.items():
        setattr(need, field, value)
    db.commit()
    return need


# --- Admin ------------------------------------------------------------------------------


def admin_list(
    db: Session, status: VerificationStatus | None, limit: int, offset: int
) -> list[OrganizationProfile]:
    query = select(OrganizationProfile)
    if status is not None:
        query = query.where(OrganizationProfile.verification_status == status)
    query = query.order_by(OrganizationProfile.created_at).limit(limit).offset(offset)
    return list(db.scalars(query))


def counts_by_status(db: Session) -> dict[VerificationStatus, int]:
    """Every verification status, with zero for those no organisation has."""
    rows = db.execute(
        select(OrganizationProfile.verification_status, func.count()).group_by(
            OrganizationProfile.verification_status
        )
    )
    counts = {status: 0 for status in VerificationStatus}
    counts.update(dict(rows.all()))
    return counts


def admin_get(db: Session, org_id: uuid.UUID) -> OrganizationProfile:
    org = db.get(OrganizationProfile, org_id)
    if org is None:
        raise NotFound("Organisation not found.")
    return org


def set_verification(
    db: Session, org_id: uuid.UUID, data: VerificationUpdate, admin: User
) -> OrganizationProfile:
    org = db.get(OrganizationProfile, org_id, with_for_update=True)
    if org is None:
        raise NotFound("Organisation not found.")
    org.verification_status = data.status
    org.verification_note = data.note
    org.verification_updated_at = datetime.now(UTC)
    org.verification_updated_by_id = admin.id
    db.commit()
    return org
