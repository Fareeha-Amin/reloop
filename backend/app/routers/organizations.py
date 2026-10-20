import uuid

from fastapi import APIRouter, status

from app.routers.common import GeocoderDep
from app.schemas.need import NeedCreate, NeedOut, NeedUpdate
from app.schemas.organization import OrganizationOut, OrganizationUpdate
from app.security.deps import AcceptorUser, DbSession
from app.services import organizations

router = APIRouter(prefix="/organisations/me", tags=["acceptor: organisation & needs"])


@router.get("", response_model=OrganizationOut)
def get_my_organisation(user: AcceptorUser, db: DbSession):
    return organizations.get_for_user(db, user)


@router.patch("", response_model=OrganizationOut)
def update_my_organisation(
    data: OrganizationUpdate, user: AcceptorUser, db: DbSession, geocoder: GeocoderDep
):
    org = organizations.get_for_user(db, user)
    return organizations.update_profile(db, org, data, geocoder)


@router.get("/needs", response_model=list[NeedOut])
def list_needs(user: AcceptorUser, db: DbSession, active_only: bool = False):
    org = organizations.get_for_user(db, user)
    return organizations.list_needs(db, org, active_only)


@router.post("/needs", response_model=NeedOut, status_code=status.HTTP_201_CREATED)
def create_need(data: NeedCreate, user: AcceptorUser, db: DbSession):
    """Unverified organisations may maintain needs; verification gates matching (Phase 2),
    not list upkeep."""
    org = organizations.get_for_user(db, user)
    return organizations.create_need(db, org, data)


@router.patch("/needs/{need_id}", response_model=NeedOut)
def update_need(need_id: uuid.UUID, data: NeedUpdate, user: AcceptorUser, db: DbSession):
    """Update quantity or urgency, or set is_active=false. Needs are never deleted."""
    org = organizations.get_for_user(db, user)
    return organizations.update_need(db, org, need_id, data)
