import uuid
from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile, status

from app.constants import IMAGE_MAX_BYTES, DonationAction
from app.routers.common import GeocoderDep, PageDep, StorageDep
from app.schemas.donation import DonationCreate, DonationImageOut, DonationOut, DonationUpdate
from app.security.deps import DbSession, DonorOrAdminUser, DonorUser
from app.services import donations
from app.services.donations import Upload

router = APIRouter(prefix="/donations", tags=["donor: donations"])


@router.post("", response_model=DonationOut, status_code=status.HTTP_201_CREATED)
def create_donation(data: DonationCreate, user: DonorUser, db: DbSession, geocoder: GeocoderDep):
    return DonationOut.from_donation(donations.create(db, user, data, geocoder))


@router.get("", response_model=list[DonationOut])
def list_my_donations(user: DonorUser, db: DbSession, page: PageDep):
    return [
        DonationOut.from_donation(d)
        for d in donations.list_for_donor(db, user, page.limit, page.offset)
    ]


@router.get("/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: uuid.UUID, user: DonorOrAdminUser, db: DbSession):
    """Readable by the donor who owns it and by admins. Anyone else gets 404."""
    return DonationOut.from_donation(donations.get_visible(db, donation_id, user))


@router.patch("/{donation_id}", response_model=DonationOut)
def update_donation(
    donation_id: uuid.UUID,
    data: DonationUpdate,
    user: DonorUser,
    db: DbSession,
    geocoder: GeocoderDep,
):
    """Only while the donation is editable (LISTED). Status cannot be set here."""
    return DonationOut.from_donation(donations.update(db, donation_id, user, data, geocoder))


@router.post("/{donation_id}/cancel", response_model=DonationOut)
def cancel_donation(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """Withdraw the donation. It is kept, with status CANCELLED, not deleted."""
    return DonationOut.from_donation(
        donations.apply_action(db, donation_id, user, DonationAction.CANCEL)
    )


@router.post(
    "/{donation_id}/images",
    response_model=list[DonationImageOut],
    status_code=status.HTTP_201_CREATED,
)
def upload_images(
    donation_id: uuid.UUID,
    files: Annotated[list[UploadFile], File(description="JPEG, PNG or WebP images.")],
    user: DonorUser,
    db: DbSession,
    storage: StorageDep,
):
    """Validated server-side and re-encoded, which strips EXIF (including GPS) and other
    metadata. All-or-nothing: if any file is rejected, none is stored."""
    # Read at most one byte past the limit, so an oversized file is detected without
    # being read into memory in full.
    uploads = [Upload(f.filename or "upload", f.file.read(IMAGE_MAX_BYTES + 1)) for f in files]
    return donations.add_images(db, donation_id, user, uploads, storage)


@router.get(
    "/{donation_id}/images/{image_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}, "image/png": {}, "image/webp": {}}}},
)
def get_image(
    donation_id: uuid.UUID,
    image_id: uuid.UUID,
    user: DonorOrAdminUser,
    db: DbSession,
    storage: StorageDep,
):
    image, data = donations.read_image(db, donation_id, image_id, user, storage)
    return Response(
        content=data,
        media_type=image.content_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{donation_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    donation_id: uuid.UUID,
    image_id: uuid.UUID,
    user: DonorUser,
    db: DbSession,
    storage: StorageDep,
):
    donations.delete_image(db, donation_id, image_id, user, storage)
