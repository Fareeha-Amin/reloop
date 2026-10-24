from fastapi import APIRouter

from app.constants import Category
from app.domain import geo
from app.schemas.discovery import DiscoveryOrganisationOut, DiscoveryOut
from app.security.deps import DbSession
from app.services import discovery

router = APIRouter(prefix="/discovery", tags=["public: discovery"])


@router.get("/organisations", response_model=DiscoveryOut)
def discover_organisations(db: DbSession, category: Category | None = None):
    """Public, no login. Verified organisations with their active needs, at positions
    rounded to about a kilometre. No address, phone, contact person or registration ID."""
    return DiscoveryOut(
        organisations=[DiscoveryOrganisationOut.from_org(o) for o in discovery.verified_organisations(db, category)],
        position_error_km=round(geo.approximation_error_km(), 1),
    )
