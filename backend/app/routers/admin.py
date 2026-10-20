import uuid

from fastapi import APIRouter

from app.constants import DonationStatus, VerificationStatus
from app.schemas.donation import DonationOut
from app.schemas.need import NeedOut
from app.schemas.organization import AdminOrganizationDetail, OrganizationOut, VerificationUpdate
from app.security.deps import AdminUser, DbSession
from app.routers.common import PageDep
from app.services import donations, organizations

router = APIRouter(prefix="/admin", tags=["admin"])


def _detail(org) -> AdminOrganizationDetail:
    base = OrganizationOut.model_validate(org).model_dump()
    return AdminOrganizationDetail(
        **base,
        account_email=org.user.email,
        needs=[NeedOut.model_validate(n) for n in org.needs],
    )


@router.get("/organisations", response_model=list[OrganizationOut])
def list_organisations(
    admin: AdminUser,
    db: DbSession,
    page: PageDep,
    verification_status: VerificationStatus | None = None,
):
    return organizations.admin_list(db, verification_status, page.limit, page.offset)


@router.get("/organisations/{org_id}", response_model=AdminOrganizationDetail)
def get_organisation(org_id: uuid.UUID, admin: AdminUser, db: DbSession):
    return _detail(organizations.admin_get(db, org_id))


@router.patch("/organisations/{org_id}/verification", response_model=AdminOrganizationDetail)
def set_verification(
    org_id: uuid.UUID, data: VerificationUpdate, admin: AdminUser, db: DbSession
):
    """The only way an organisation's verification status changes. Records which admin
    changed it and when."""
    return _detail(organizations.set_verification(db, org_id, data, admin))


@router.get("/donations", response_model=list[DonationOut])
def list_donations(
    admin: AdminUser,
    db: DbSession,
    page: PageDep,
    status: DonationStatus | None = None,
):
    return [
        DonationOut.from_donation(d)
        for d in donations.admin_list(db, status, page.limit, page.offset)
    ]
