from sqlalchemy import func, select

from app.constants import Category, VerificationStatus
from app.domain.geo import haversine_km
from app.models import CurrentNeed, LogisticsProvider, OrganizationProfile, User, WasteCollector
from app.services import seed
from tests.api import helpers as h

# The original seed. Registration IDs follow position, so these stay first and in this order.
ORIGINAL_ORGANISATIONS = 10
ORIGINAL_RECYCLERS = 3
ORIGINAL_ORG_SLUGS = (
    "asha-kiran", "koramangala-shelter", "jayanagar-reading-room", "malleshwaram-seva", "hsr-womens-shelter",
    "whitefield-schools", "yelahanka-elders", "ecity-collective", "banashankari-toys", "hebbal-shelter",
)
ORIGINAL_RECYCLER_NAMES = ("GreenCycle Textile Recovery", "PaperLoop Recyclers", "Old Town Scrap Traders")
BENGALURU = {"lat": (12.80, 13.15), "lng": (77.40, 77.80)}  # the city and its edges


def _counts(db) -> tuple[int, int, int, int, int]:
    return tuple(
        db.scalar(select(func.count()).select_from(m))
        for m in (OrganizationProfile, WasteCollector, LogisticsProvider, User, CurrentNeed)
    )


def test_seed_is_idempotent(db):
    first = seed.seed(db, h.PASSWORD)
    assert len(first.organisations_created) == len(seed.ORGANISATIONS) and first.donor_created
    assert len(first.recyclers_created) == len(seed.RECYCLERS)
    assert len(first.providers_created) == len(seed.LOGISTICS_PROVIDERS)
    after_first = _counts(db)

    second = seed.seed(db, h.PASSWORD)
    assert second.organisations_created == [] and second.recyclers_created == [] and not second.donor_created
    assert second.providers_created == []
    assert len(second.organisations_existing) == len(seed.ORGANISATIONS)
    assert _counts(db) == after_first


def test_reseeding_a_database_that_has_only_the_original_seed_adds_just_the_additions(db, monkeypatch):
    """The real situation: dev was seeded before the coverage additions existed. Running seed
    again must add only the new rows and leave the original ones exactly as they were."""
    monkeypatch.setattr(seed, "ORGANISATIONS", seed.ORGANISATIONS[:ORIGINAL_ORGANISATIONS])
    monkeypatch.setattr(seed, "RECYCLERS", seed.RECYCLERS[:ORIGINAL_RECYCLERS])
    seed.seed(db, h.PASSWORD)
    original_ids = {o.registration_id: o.id for o in db.scalars(select(OrganizationProfile))}
    assert len(original_ids) == ORIGINAL_ORGANISATIONS
    monkeypatch.undo()

    report = seed.seed(db, h.PASSWORD)

    added = len(seed.ORGANISATIONS) - ORIGINAL_ORGANISATIONS
    assert len(report.organisations_created) == added and len(report.organisations_existing) == ORIGINAL_ORGANISATIONS
    assert len(report.recyclers_created) == len(seed.RECYCLERS) - ORIGINAL_RECYCLERS
    assert not report.donor_created
    after = {o.registration_id: o.id for o in db.scalars(select(OrganizationProfile))}
    assert all(after[reg] == org_id for reg, org_id in original_ids.items()), "an original organisation changed identity"
    assert len(after) == len(seed.ORGANISATIONS)


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


# --- The seed data itself (no database needed) ---------------------------------------------------


def test_the_original_seed_keeps_its_identity_and_order():
    """Registration IDs are positions, so inserting or reordering would re-key real rows."""
    assert tuple(o.slug for o in seed.ORGANISATIONS[:ORIGINAL_ORGANISATIONS]) == ORIGINAL_ORG_SLUGS
    assert tuple(r.name for r in seed.RECYCLERS[:ORIGINAL_RECYCLERS]) == ORIGINAL_RECYCLER_NAMES


def test_there_are_at_least_ten_added_organisations_and_ten_added_recyclers():
    assert len(seed.ORGANISATIONS) - ORIGINAL_ORGANISATIONS >= 10
    assert len(seed.RECYCLERS) - ORIGINAL_RECYCLERS >= 10


def test_seed_identifiers_are_unique():
    for values in (
        [o.slug for o in seed.ORGANISATIONS],
        [o.name for o in seed.ORGANISATIONS],
        [o.email for o in seed.ORGANISATIONS],
        [r.name for r in seed.RECYCLERS],
    ):
        assert len(values) == len(set(values))


def test_every_seeded_place_is_inside_bengaluru():
    places = [(o.name, o.lat, o.lng) for o in seed.ORGANISATIONS] + [(r.name, r.lat, r.lng) for r in seed.RECYCLERS]
    for name, lat, lng in places:
        assert BENGALURU["lat"][0] <= lat <= BENGALURU["lat"][1], name
        assert BENGALURU["lng"][0] <= lng <= BENGALURU["lng"][1], name


def test_the_additions_keep_the_original_layout_intact():
    """Every added organisation is verified, every added recycler is active, and none of the
    recyclers takes toys: the counts the acceptance flows rely on do not move."""
    assert all(o.verification == VerificationStatus.VERIFIED for o in seed.ORGANISATIONS[ORIGINAL_ORGANISATIONS:])
    added = seed.RECYCLERS[ORIGINAL_RECYCLERS:]
    assert all(r.is_active for r in added)
    assert not any(Category.TOYS in r.categories for r in seed.RECYCLERS)


def test_the_additions_do_not_reach_nelamangala_so_that_acceptance_flow_still_holds():
    nelamangala = h.NELAMANGALA
    assert all(haversine_km(*nelamangala, o.lat, o.lng) > 15.0 for o in seed.ORGANISATIONS)
    greencycle = next(r for r in seed.RECYCLERS if r.name == "GreenCycle Textile Recovery")
    nearest_green = haversine_km(*nelamangala, greencycle.lat, greencycle.lng)
    assert all(
        haversine_km(*nelamangala, r.lat, r.lng) > nearest_green for r in seed.RECYCLERS if r is not greencycle
    ), "GreenCycle must remain the nearest recycler to a Nelamangala donation"


def test_the_additions_cover_the_west_east_north_and_south_of_the_city():
    places = [(o.lat, o.lng) for o in seed.ORGANISATIONS[ORIGINAL_ORGANISATIONS:]]
    places += [(r.lat, r.lng) for r in seed.RECYCLERS[ORIGINAL_RECYCLERS:]]
    assert any(lng < 77.52 for _, lng in places), "nothing added in the west"
    assert any(lng > 77.69 for _, lng in places), "nothing added in the east"
    assert any(lat > 13.04 for lat, _ in places), "nothing added in the north"
    assert any(lat < 12.91 for lat, _ in places), "nothing added in the south"
