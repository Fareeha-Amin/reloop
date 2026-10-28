import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from app.constants import Actor, DonationStatus, VerificationStatus
from app.domain import lifecycle
from app.routers.common import PageDep
from app.routers.donations import donation_out
from app.schemas.admin import (
    AdminDonationDetailOut,
    CommissionEntryOut,
    CommissionSummaryOut,
    QueueItemOut,
    RankingRunOut,
    RecyclerOut,
    SweepReportOut,
)
from app.schemas.donation import DonationOut, DonationSummaryOut
from app.schemas.matching import ReasonIn
from app.schemas.need import NeedOut
from app.schemas.organization import (
    AdminOrganizationDetail,
    OrganizationCountsOut,
    OrganizationOut,
    VerificationUpdate,
)
from app.security.deps import AdminUser, DbSession
from app.services import actions, admin as admin_views, commission, donations, organizations, sweeper, timeline

router = APIRouter(prefix="/admin", tags=["admin"])


def _now() -> datetime:
    return datetime.now(UTC)


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


@router.get("/organisations/counts", response_model=OrganizationCountsOut)
def organisation_counts(admin: AdminUser, db: DbSession):
    """How many organisations are in each verification status, and how many await an
    admin's decision (every organisation starts PENDING)."""
    counts = organizations.counts_by_status(db)
    return OrganizationCountsOut(by_status=counts, awaiting_verification=counts[VerificationStatus.PENDING])


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


# --- Donations ------------------------------------------------------------------------------


def _queue_item(db, entry) -> QueueItemOut:
    return QueueItemOut(
        donation=DonationSummaryOut.model_validate(entry.donation),
        entered_at=entry.entered_at,
        from_state=entry.from_state,
        via=entry.via,
        allowed_actions=sorted(actions.available(db, entry.donation, Actor.ADMIN)),
    )


@router.get("/donations", response_model=list[DonationSummaryOut])
def list_donations(
    admin: AdminUser,
    db: DbSession,
    page: PageDep,
    status: DonationStatus | None = None,
):
    """Without addresses. The precise address is in the detail, where each read is recorded."""
    return donations.admin_list(db, status, page.limit, page.offset)


@router.get("/queue", response_model=list[QueueItemOut])
def unroutable_queue(admin: AdminUser, db: DbSession):
    """Donations that could not be routed (NEEDS_ADMIN), longest-waiting first, with the
    transition that put each one here and what can be done about it."""
    return [_queue_item(db, e) for e in admin_views.queue(db)]


@router.get("/awaiting", response_model=list[QueueItemOut])
def awaiting_admin(admin: AdminUser, db: DbSession):
    """Every donation waiting on an admin: the states with an admin action out of them
    (lifecycle.states_awaiting(ADMIN): the unroutable queue, and recycling to confirm),
    longest-waiting first, with the transition that put each one there and what can be
    done about it."""
    return [_queue_item(db, e) for e in admin_views.awaiting(db, lifecycle.states_awaiting(Actor.ADMIN))]


@router.get("/donations/{donation_id}", response_model=AdminDonationDetailOut)
def get_donation_detail(donation_id: uuid.UUID, admin: AdminUser, db: DbSession):
    """Full detail, including the precise address. This read is recorded."""
    donation = donations.read(db, donation_id, admin, _now())
    return AdminDonationDetailOut(
        donation=donation_out(db, donation, admin),
        timeline=timeline.build(db, donation, for_admin=True),
        ranking_runs=[RankingRunOut.model_validate(r) for r in admin_views.ranking_runs(db, donation.id)],
    )


@router.post("/donations/{donation_id}/requeue", response_model=DonationOut)
def requeue(donation_id: uuid.UUID, data: ReasonIn, admin: AdminUser, db: DbSession):
    """NEEDS_ADMIN → back into matching: re-offered at once, or escalated to the donor if
    the decline threshold is still reached. Offered only while the slate is non-empty."""
    return donation_out(db, actions.admin_requeue(db, donation_id, admin, data.reason, _now()), admin)


@router.post("/donations/{donation_id}/redirect-to-recycling", response_model=DonationOut)
def redirect_to_recycling(donation_id: uuid.UUID, data: ReasonIn, admin: AdminUser, db: DbSession):
    """NEEDS_ADMIN → WASTE_REDIRECTED. Offered only if a recycler can take it."""
    return donation_out(
        db, actions.admin_redirect_to_recycling(db, donation_id, admin, data.reason, _now()), admin
    )


@router.post("/donations/{donation_id}/cancel", response_model=DonationOut)
def cancel(donation_id: uuid.UUID, data: ReasonIn, admin: AdminUser, db: DbSession):
    """NEEDS_ADMIN → CANCELLED."""
    return donation_out(db, actions.admin_cancel(db, donation_id, admin, data.reason, _now()), admin)


@router.post("/donations/{donation_id}/confirm-recycled", response_model=DonationOut)
def confirm_recycled(donation_id: uuid.UUID, data: ReasonIn, admin: AdminUser, db: DbSession):
    """RECYCLING_IN_TRANSIT → RECYCLED, once the donor's own handover to the recycler
    is recorded (drop-off or a platform pickup) — never straight from
    WASTE_REDIRECTED; there is no recycler login to confirm receipt any other way.
    SIMULATED: the admin confirms on the recycler's behalf, and a simulated settlement
    over estimated mass is recorded (see the donation's timeline). No money moves."""
    return donation_out(
        db, actions.admin_confirm_recycled(db, donation_id, admin, data.reason, _now()), admin
    )


# --- Sweeper and recyclers --------------------------------------------------------------------


@router.post("/sweep", response_model=SweepReportOut)
def run_sweep(admin: AdminUser, db: DbSession):
    """Apply every due deadline now: expired offers, donations never offered, silent
    donors and stalled handovers. Safe to run repeatedly. Also: python -m app.cli sweep."""
    return sweeper.sweep(db, _now())


@router.get("/recyclers", response_model=list[RecyclerOut])
def list_recyclers(admin: AdminUser, db: DbSession):
    return admin_views.recyclers(db)


@router.get("/commission", response_model=CommissionSummaryOut)
def commission_summary(admin: AdminUser, db: DbSession, page: PageDep):
    """The platform's earnings ledger: logistics fees and recycling fees. A cancelled,
    undelivered booking's commission is reversed by a second, negated row, so `total`
    is always net. SIMULATED: no money actually moves."""
    return CommissionSummaryOut(
        total=commission.total(db),
        entries=[CommissionEntryOut.model_validate(e) for e in commission.recent(db, page.limit, page.offset)],
    )
