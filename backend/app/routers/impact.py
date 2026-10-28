from fastapi import APIRouter

from app.schemas.impact import ImpactTotalsOut
from app.security.deps import AcceptorUser, DbSession, DonorUser
from app.services import impact, organizations

router = APIRouter(prefix="/impact", tags=["impact (estimates)"])


@router.get("/me", response_model=ImpactTotalsOut)
def my_impact(user: DonorUser, db: DbSession):
    """The donor's totals over their finished donations: reused and recycled, separately.
    Estimates, labelled as such."""
    return ImpactTotalsOut.build(impact.donor_totals(db, user.id))


@router.get("/organisation", response_model=ImpactTotalsOut)
def organisation_impact(user: AcceptorUser, db: DbSession):
    """The organisation's reuse totals: donations it accepted and that were completed.
    Recycling is not credited to an organisation. Estimates, labelled as such."""
    org = organizations.get_for_user(db, user)
    return ImpactTotalsOut.build(impact.organisation_totals(db, org.id))
