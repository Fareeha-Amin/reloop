"""Donation CRUD and images. Status changes live in app.services.actions (donor and
admin) and app.services.offers (acceptor); this module never compares statuses itself."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import IMAGES_PER_DONATION_MAX, AddressAccess, DonationStatus, Role
from app.domain import lifecycle
from app.models import Donation, DonationImage, User
from app.schemas.donation import DonationCreate, DonationUpdate, validate_pickup_window
from app.services import audit, matching, organizations
from app.services.errors import Conflict, NotFound, Unprocessable
from app.services.geocoding import Geocoder
from app.services.images import ImageRejected, process_upload
from app.services.storage import ImageStorage

logger = logging.getLogger(__name__)


def create(db: Session, donor: User, data: DonationCreate, geocoder: Geocoder) -> Donation:
    location = geocoder.resolve(
        data.pickup_address_text, data.pickup_latitude, data.pickup_longitude
    )
    donation = Donation(
        donor_id=donor.id,
        category=data.category,
        quantity=data.quantity,
        condition=data.condition,
        note=data.note,
        is_priority=data.is_priority,
        pickup_address_text=location.address_text,
        pickup_latitude=location.latitude,
        pickup_longitude=location.longitude,
        pickup_window_start=data.pickup_window_start,
        pickup_window_end=data.pickup_window_end,
        status=lifecycle.INITIAL_STATE,
    )
    db.add(donation)
    db.commit()
    return donation


def list_for_donor(db: Session, donor: User, limit: int, offset: int) -> list[Donation]:
    query = (
        select(Donation)
        .where(Donation.donor_id == donor.id)
        .order_by(Donation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query))


def admin_list(
    db: Session, status: DonationStatus | None, limit: int, offset: int
) -> list[Donation]:
    """Returned redacted (no address): reading the precise address is a logged detail
    read, not a side effect of listing."""
    query = select(Donation)
    if status is not None:
        query = query.where(Donation.status == status)
    query = query.order_by(Donation.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(query))


def get_visible(db: Session, donation_id: uuid.UUID, user: User, lock: bool = False) -> Donation:
    """The full donation (including the precise address): the donor who owns it, or an
    admin. Anyone else gets the same 404 as for a donation that does not exist.
    Acceptors use the redacted views in app.services.offers instead."""
    donation = db.get(Donation, donation_id, with_for_update=lock)
    if donation is None:
        raise NotFound("Donation not found.")
    if user.role != Role.ADMIN and donation.donor_id != user.id:
        raise NotFound("Donation not found.")
    return donation


def read(db: Session, donation_id: uuid.UUID, user: User, now: datetime) -> Donation:
    """get_visible, recording the access when an admin reads the precise address."""
    donation = get_visible(db, donation_id, user)
    if user.role == Role.ADMIN:
        audit.record_address_access(db, donation, user, AddressAccess.ADMIN_VIEWED, now)
        db.commit()
    return donation


def _get_owned(db: Session, donation_id: uuid.UUID, donor: User) -> Donation:
    """The donor's own donation, row-locked for the rest of the transaction so that an
    edit and a cancel cannot interleave."""
    donation = db.get(Donation, donation_id, with_for_update=True)
    if donation is None or donation.donor_id != donor.id:
        raise NotFound("Donation not found.")
    return donation


def _require_editable(donation: Donation) -> None:
    if not lifecycle.is_editable(donation.status):
        raise Conflict(f"A {donation.status.value} donation can no longer be edited.")


def update(
    db: Session, donation_id: uuid.UUID, donor: User, data: DonationUpdate, geocoder: Geocoder
) -> Donation:
    donation = _get_owned(db, donation_id, donor)
    _require_editable(donation)
    changes = data.model_dump(exclude_unset=True)

    if "pickup_window_start" in changes or "pickup_window_end" in changes:
        try:
            validate_pickup_window(
                changes.get("pickup_window_start", donation.pickup_window_start),
                changes.get("pickup_window_end", donation.pickup_window_end),
            )
        except ValueError as exc:
            raise Unprocessable(str(exc)) from exc

    # The schema guarantees an address change always comes with new coordinates.
    if "pickup_latitude" in changes:
        location = geocoder.resolve(
            changes.get("pickup_address_text", donation.pickup_address_text),
            changes["pickup_latitude"],
            changes["pickup_longitude"],
        )
        changes["pickup_address_text"] = location.address_text
        changes["pickup_latitude"] = location.latitude
        changes["pickup_longitude"] = location.longitude

    for field, value in changes.items():
        setattr(donation, field, value)
    db.commit()
    return donation


# --- Images -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Upload:
    filename: str
    data: bytes


def add_images(
    db: Session,
    donation_id: uuid.UUID,
    donor: User,
    uploads: list[Upload],
    storage: ImageStorage,
) -> list[DonationImage]:
    """All-or-nothing: every file is validated before any is stored, and stored files are
    removed again if the database write fails."""
    donation = _get_owned(db, donation_id, donor)
    _require_editable(donation)
    if not uploads:
        raise Unprocessable("No files were uploaded.")

    existing = db.scalar(
        select(func.count()).select_from(DonationImage).where(DonationImage.donation_id == donation.id)
    )
    if existing + len(uploads) > IMAGES_PER_DONATION_MAX:
        raise Conflict(
            f"A donation can have at most {IMAGES_PER_DONATION_MAX} images "
            f"({existing} already attached)."
        )

    processed = []
    for upload in uploads:
        try:
            processed.append(process_upload(upload.data))
        except ImageRejected as exc:
            raise Unprocessable(f"{upload.filename}: {exc}") from exc

    saved_keys: list[str] = []
    try:
        images = []
        for item in processed:
            key = storage.save(item.data, item.extension)
            saved_keys.append(key)
            image = DonationImage(
                donation_id=donation.id,
                storage_key=key,
                content_type=item.content_type,
                size_bytes=len(item.data),
            )
            db.add(image)
            images.append(image)
        db.commit()
    except Exception:
        db.rollback()
        for key in saved_keys:
            storage.delete(key)
        raise
    return images


def _get_image(db: Session, donation: Donation, image_id: uuid.UUID) -> DonationImage:
    image = db.get(DonationImage, image_id)
    if image is None or image.donation_id != donation.id:
        raise NotFound("Image not found.")
    return image


def _image_visible_donation(db: Session, donation_id: uuid.UUID, user: User) -> Donation:
    """Images (EXIF-stripped at upload) are visible to the donor, admins, and an
    organisation while it has an open offer for the donation or holds it."""
    if user.role == Role.ACCEPTOR:
        org = organizations.get_for_user(db, user)
        donation = db.get(Donation, donation_id)
        if donation is None or not matching.organisation_may_see_images(db, donation_id, org.id):
            raise NotFound("Donation not found.")
        return donation
    return get_visible(db, donation_id, user)


def read_image(
    db: Session, donation_id: uuid.UUID, image_id: uuid.UUID, user: User, storage: ImageStorage
) -> tuple[DonationImage, bytes]:
    donation = _image_visible_donation(db, donation_id, user)
    image = _get_image(db, donation, image_id)
    try:
        return image, storage.read(image.storage_key)
    except FileNotFoundError:
        # Never pretend: a row whose file is gone is a real fault, so log it loudly.
        logger.error("Image %s has a database row but no stored file (%s).", image.id, image.storage_key)
        raise NotFound("Image file is missing.") from None


def delete_image(
    db: Session, donation_id: uuid.UUID, image_id: uuid.UUID, donor: User, storage: ImageStorage
) -> None:
    donation = _get_owned(db, donation_id, donor)
    _require_editable(donation)
    image = _get_image(db, donation, image_id)
    key = image.storage_key
    db.delete(image)
    db.commit()
    # Delete the file after the row: a leftover file is harmless, a row pointing at a
    # missing file is not.
    try:
        storage.delete(key)
    except OSError:
        logger.exception("Image row %s deleted but its file %s could not be removed.", image_id, key)
