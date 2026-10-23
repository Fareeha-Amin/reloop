import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, File, Response, UploadFile, status

from app.constants import IMAGE_MAX_BYTES, Actor, Role
from app.models import Donation, User
from app.routers.common import GeocoderDep, PageDep, StorageDep
from app.schemas.donation import DonationCreate, DonationImageOut, DonationOut, DonationUpdate
from app.schemas.matching import OfferCreate, ScheduleIn, SlateOut
from app.schemas.timeline import TimelineOut
from app.security.deps import CurrentUser, DbSession, DonorOrAdminUser, DonorUser
from app.services import actions, donations, matching, timeline
from app.services.donations import Upload

router = APIRouter(prefix="/donations", tags=["donor: donations"])


def _now() -> datetime:
    return datetime.now(UTC)


def donation_out(db, donation: Donation, viewer: User) -> DonationOut:
    actor = Actor.ADMIN if viewer.role == Role.ADMIN else Actor.DONOR
    return DonationOut.from_donation(
        donation,
        actions.available(db, donation, actor),
        actions.escalation_cause(db, donation),
    )


@router.post("", response_model=DonationOut, status_code=status.HTTP_201_CREATED)
def create_donation(data: DonationCreate, user: DonorUser, db: DbSession, geocoder: GeocoderDep):
    return donation_out(db, donations.create(db, user, data, geocoder), user)


@router.get("", response_model=list[DonationOut])
def list_my_donations(user: DonorUser, db: DbSession, page: PageDep):
    return [
        donation_out(db, d, user) for d in donations.list_for_donor(db, user, page.limit, page.offset)
    ]


@router.get("/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: uuid.UUID, user: DonorOrAdminUser, db: DbSession):
    """Readable by the donor who owns it and by admins. Anyone else gets 404. An admin
    read of the precise address is recorded."""
    return donation_out(db, donations.read(db, donation_id, user, _now()), user)


@router.patch("/{donation_id}", response_model=DonationOut)
def update_donation(
    donation_id: uuid.UUID,
    data: DonationUpdate,
    user: DonorUser,
    db: DbSession,
    geocoder: GeocoderDep,
):
    """Only while the donation is editable (LISTED). Status cannot be set here."""
    return donation_out(db, donations.update(db, donation_id, user, data, geocoder), user)


@router.get("/{donation_id}/timeline", response_model=TimelineOut)
def get_timeline(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """Status events, every offer and its response, and any recycling (simulated)."""
    donation = donations.get_visible(db, donation_id, user)
    return timeline.build(db, donation, for_admin=False)


# --- Matching and lifecycle actions --------------------------------------------------------


@router.get("/{donation_id}/candidates", response_model=SlateOut)
def get_candidates(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """The eligible organisations, best first, each score broken into its factors. A
    preview: nothing is stored. Offering re-ranks and stores the slate it used."""
    donation = donations.get_visible(db, donation_id, user)
    slate, n = matching.compute_slate(db, donation)
    return SlateOut.from_slate(slate, n, matching.DEFAULT_CONFIG.version())


@router.post("/{donation_id}/offer", response_model=DonationOut)
def offer(
    donation_id: uuid.UUID,
    user: DonorUser,
    db: DbSession,
    data: Annotated[OfferCreate | None, Body()] = None,
):
    """LISTED → MATCHED: offer to the top candidate, or to `organization_id` if it is in
    the eligible slate. If the slate is empty the donation escalates instead
    (status ESCALATED, escalation_cause NO_CANDIDATES)."""
    org_id = data.organization_id if data else None
    return donation_out(db, actions.offer(db, donation_id, user, org_id, _now()), user)


@router.post("/{donation_id}/cancel", response_model=DonationOut)
def cancel_donation(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """Withdraw the donation (from LISTED, MATCHED or ESCALATED). It is kept, with status
    CANCELLED, not deleted. An open offer is closed as RETRACTED."""
    return donation_out(db, actions.cancel(db, donation_id, user, _now()), user)


@router.post("/{donation_id}/rematch", response_model=DonationOut)
def rematch(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """ESCALATED → re-offer to the next candidate. Offered only while the slate is
    non-empty."""
    return donation_out(db, actions.rematch(db, donation_id, user, _now()), user)


@router.post("/{donation_id}/upgrade-priority", response_model=DonationOut)
def upgrade_priority(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """As rematch, and flags the donation as priority. Priority orders acceptors' inboxes;
    it does not change which organisations are eligible or how they are ranked."""
    return donation_out(db, actions.rematch(db, donation_id, user, _now(), upgrade_priority=True), user)


@router.post("/{donation_id}/redirect-to-recycling", response_model=DonationOut)
def redirect_to_recycling(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """ESCALATED → WASTE_REDIRECTED, routed to the nearest active recycler for the
    category. If there is none, the donation goes to the admin queue (NEEDS_ADMIN)."""
    return donation_out(db, actions.redirect_to_recycling(db, donation_id, user, _now()), user)


@router.post("/{donation_id}/choose-dropoff", response_model=DonationOut)
def choose_dropoff(donation_id: uuid.UUID, data: ScheduleIn, user: DonorUser, db: DbSession):
    """ACCEPTED → PICKUP_SCHEDULED, the donor delivering. The time must be in the future."""
    return donation_out(db, actions.choose_dropoff(db, donation_id, user, data.scheduled_for, _now()), user)


@router.post("/{donation_id}/mark-handed-over", response_model=DonationOut)
def mark_handed_over(donation_id: uuid.UUID, user: DonorUser, db: DbSession):
    """PICKUP_SCHEDULED → IN_TRANSIT: the donor has handed the goods over."""
    return donation_out(db, actions.mark_handed_over(db, donation_id, user, _now()), user)


# --- Images -----------------------------------------------------------------------------------


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
    user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
):
    """The donor, admins, and an organisation while it has an open offer for the
    donation or holds it."""
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
