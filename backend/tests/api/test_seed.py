from sqlalchemy import func, select

from app.constants import Category, VerificationStatus
from app.domain.geo import haversine_km
from app.models import CurrentNeed, OrganizationProfile, User, WasteCollector
from app.services import seed
from tests.api import helpers as h


def _counts(db) -> tuple[int, int, int, int]:
    return tuple(db.scalar(select(func.count()).select_from(m)) for m in (OrganizationProfile, WasteCollector, User, CurrentNeed))


def test_seed_is_idempotent(db):
    first = seed.seed(db, h.PASSWORD)
    assert len(first.organisations_created) == 10 and len(first.recyclers_created) == 3 and first.donor_created
    after_first = _counts(db)

    second = seed.seed(db, h.PASSWORD)
    assert second.organisations_created == [] and second.recyclers_created == [] and not second.donor_created
    assert len(second.organisations_existing) == 10
    assert _counts(db) == after_first


def test_seed_layout_supports_the_acceptance_test(db):
    seed.seed(db, h.PASSWORD)
    orgs = list(db.scalars(select(OrganizationProfile).where(OrganizationProfile.registration_id.like("SEED-%"))))
    statuses = [o.verification_status for o in orgs]
    assert statuses.count(VerificationStatus.PENDING) == 2 and statuses.count(VerificationStatus.REJECTED) == 1

    donor_at = h.INDIRANAGAR
    clothes_within_15 = [
        o for o in orgs
        if o.verification_status == VerificationStatus.VERIFIED and Category.CLOTHES in o.categories_accepted
        and haversine_km(*donor_at, o.latitude, o.longitude) <= 15
    ]
    assert len(clothes_within_15) >= 4  # three rejections to escalate, then one to complete

    recyclers = list(db.scalars(select(WasteCollector)))
    assert [r.is_active for r in recyclers].count(False) == 1
    assert not any(Category.TOYS in r.categories_accepted for r in recyclers)


def test_seeded_accounts_can_log_in(client, db):
    seed.seed(db, h.PASSWORD)
    assert h.login(client, seed.DEMO_DONOR_EMAIL)["access_token"]
    assert h.login(client, seed.ORGANISATIONS[0].email)["access_token"]
