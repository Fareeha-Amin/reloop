"""Bengaluru seed data for development and the manual acceptance test.

Idempotent: organisations are keyed by registration ID, recyclers by name and the demo
donor by email. Anything that already exists is left exactly as it is (never updated,
never deleted), so running the seed twice changes nothing.

All names are fictional. Coordinates are real Bengaluru neighbourhoods. The layout is
deliberate:
- five verified CLOTHES organisations within 15 km of Indiranagar, and a sixth
  (Yelahanka, ~16 km) that only enters the slate once the radius widens after a decline;
- three organisations that never enter matching (two PENDING, one REJECTED);
- two active recyclers and one inactive one, none of which accepts TOYS, so a toy
  donation redirected to recycling lands in the admin queue (NEEDS_ADMIN).

Coverage additions (for demonstrations across the whole city): twelve more verified
organisations and twelve more active recyclers, spread over the north-west, north,
north-east, east, south-east, south, south-west and west. They are APPENDED: an
organisation's registration ID follows its position in ORGANISATIONS, so the original ten
(SEED-BLR-001 to 010) must never be reordered or have anything inserted before them. The
additions keep the layout above intact: every added organisation is verified, every added
recycler is active and takes only CLOTHES and/or BOOKS (still no TOYS), and none lies
within reach of Nelamangala, so a donation from there still has no organisation to offer
to and still goes to GreenCycle (tests/api/test_acceptance_script.py relies on both).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Category, Urgency, VerificationStatus
from app.models import CurrentNeed, LogisticsProvider, OrganizationProfile, WasteCollector
from app.schemas.organization import AcceptorRegister
from app.schemas.user import DonorRegister
from app.services import users
from app.services.geocoding import PassthroughGeocoder

C, T, B = Category.CLOTHES, Category.TOYS, Category.BOOKS
V, P, R = VerificationStatus.VERIFIED, VerificationStatus.PENDING, VerificationStatus.REJECTED
SEED_EMAIL_DOMAIN = "example.org"
DEMO_DONOR_EMAIL = f"demo.donor@{SEED_EMAIL_DOMAIN}"


@dataclass(frozen=True)
class SeedOrg:
    slug: str
    name: str
    address: str
    lat: float
    lng: float
    categories: tuple[Category, ...]
    capacity: int
    pickup_capable: bool
    verification: VerificationStatus
    needs: tuple[tuple[Category, int, Urgency], ...] = ()

    @property
    def email(self) -> str:
        return f"seed.{self.slug}@{SEED_EMAIL_DOMAIN}"


ORGANISATIONS: tuple[SeedOrg, ...] = (
    SeedOrg("asha-kiran", "Asha Kiran Children's Home", "14 CMH Road, Indiranagar, Bengaluru",
            12.9719, 77.6412, (C, T, B), 300, True, V, ((C, 50, Urgency.HIGH), (T, 20, Urgency.MEDIUM))),
    SeedOrg("koramangala-shelter", "Koramangala Community Shelter", "80 Feet Road, Koramangala 4th Block, Bengaluru",
            12.9352, 77.6245, (C, B), 200, True, V, ((C, 40, Urgency.MEDIUM),)),
    SeedOrg("jayanagar-reading-room", "Jayanagar Reading Room Trust", "11th Main, Jayanagar 4th Block, Bengaluru",
            12.9250, 77.5938, (B,), 500, False, V, ((B, 100, Urgency.HIGH),)),
    SeedOrg("malleshwaram-seva", "Malleshwaram Seva Samithi", "Sampige Road, Malleshwaram, Bengaluru",
            13.0035, 77.5710, (C, T), 150, True, V, ((T, 10, Urgency.LOW),)),
    SeedOrg("hsr-womens-shelter", "HSR Women's Shelter", "27th Main, HSR Layout Sector 1, Bengaluru",
            12.9116, 77.6474, (C,), 120, False, V),
    SeedOrg("whitefield-schools", "Whitefield Rural Schools Network", "ITPL Main Road, Whitefield, Bengaluru",
            12.9698, 77.7500, (C, T, B), 400, True, V, ((B, 80, Urgency.MEDIUM),)),
    SeedOrg("yelahanka-elders", "Yelahanka Elders' Home", "Doddaballapur Road, Yelahanka New Town, Bengaluru",
            13.1155, 77.5960, (C,), 100, True, V, ((C, 30, Urgency.LOW),)),
    SeedOrg("ecity-collective", "E-City Migrant Workers' Collective", "Hosur Road, Electronic City Phase 1, Bengaluru",
            12.8452, 77.6602, (C,), 250, True, P),
    SeedOrg("banashankari-toys", "Banashankari Toy Library", "BSK 2nd Stage, Banashankari, Bengaluru",
            12.9255, 77.5468, (T, B), 80, False, P, ((T, 25, Urgency.HIGH),)),
    SeedOrg("hebbal-shelter", "Hebbal Night Shelter", "Bellary Road, Hebbal, Bengaluru",
            13.0358, 77.5970, (C, B), 150, True, R),
    # --- Coverage additions: append only (registration IDs follow position). All verified. ---
    SeedOrg("rajajinagar-aid", "Rajajinagar Neighbourhood Aid Society", "Dr Rajkumar Road, Rajajinagar, Bengaluru",
            12.9915, 77.5520, (C, B), 180, True, V, ((C, 35, Urgency.MEDIUM),)),
    SeedOrg("jalahalli-vidya", "Jalahalli Vidya Trust", "Jalahalli East, Bengaluru",
            13.0480, 77.5530, (B, T), 250, False, V, ((B, 60, Urgency.HIGH), (T, 15, Urgency.LOW))),
    SeedOrg("yeshwanthpur-seva", "Yeshwanthpur Seva Kendra", "Tumkur Road, Yeshwanthpur, Bengaluru",
            13.0280, 77.5400, (C, T), 140, True, V, ((C, 25, Urgency.HIGH),)),
    SeedOrg("sahakara-elders", "Sahakara Nagar Elders' Care", "Sahakara Nagar, Bengaluru",
            13.0620, 77.5870, (C, B), 90, False, V, ((C, 20, Urgency.LOW),)),
    SeedOrg("hennur-learning", "Hennur Learning Centre", "Hennur Main Road, Bengaluru",
            13.0400, 77.6420, (C, T, B), 220, True, V, ((T, 30, Urgency.MEDIUM),)),
    SeedOrg("krpuram-workers", "KR Puram Workers' Forum", "Old Madras Road, KR Puram, Bengaluru",
            13.0070, 77.6960, (C,), 300, True, V, ((C, 60, Urgency.HIGH),)),
    SeedOrg("marathahalli-hope", "Marathahalli Hope Home", "Outer Ring Road, Marathahalli, Bengaluru",
            12.9560, 77.7010, (C, T, B), 200, True, V, ((T, 18, Urgency.HIGH), (B, 40, Urgency.MEDIUM))),
    SeedOrg("bellandur-shelter", "Bellandur Lakeside Shelter", "Sarjapur Road, Bellandur, Bengaluru",
            12.9260, 77.6760, (C, B), 160, False, V),
    SeedOrg("bannerghatta-home", "Bannerghatta Road Children's Home", "Bannerghatta Main Road, Bengaluru",
            12.8890, 77.5960, (C, T, B), 260, True, V, ((C, 45, Urgency.MEDIUM), (T, 22, Urgency.HIGH))),
    SeedOrg("jpnagar-reading", "JP Nagar Reading Circle", "24th Main, JP Nagar 2nd Phase, Bengaluru",
            12.9070, 77.5850, (B, T), 400, False, V, ((B, 90, Urgency.MEDIUM),)),
    SeedOrg("kengeri-trust", "Kengeri Community Trust", "Mysore Road, Kengeri, Bengaluru",
            12.9170, 77.4830, (C, B), 350, True, V, ((C, 70, Urgency.HIGH),)),
    SeedOrg("rrnagar-women", "RR Nagar Women's Collective", "Rajarajeshwari Nagar, Bengaluru",
            12.9270, 77.5190, (C, T), 110, True, V, ((C, 25, Urgency.MEDIUM),)),
)  # fmt: skip


@dataclass(frozen=True)
class SeedRecycler:
    name: str
    address: str
    lat: float
    lng: float
    categories: tuple[Category, ...]
    rate_per_kg: Decimal
    is_active: bool


# None accepts TOYS (deliberately). The first three are the original seed; the rest are coverage additions.
RECYCLERS: tuple[SeedRecycler, ...] = (
    SeedRecycler("GreenCycle Textile Recovery", "Peenya Industrial Area, Bengaluru",
                 13.0285, 77.5197, (C,), Decimal("12.00"), True),
    SeedRecycler("PaperLoop Recyclers", "Bommanahalli, Hosur Road, Bengaluru",
                 12.9081, 77.6237, (B, C), Decimal("8.50"), True),
    SeedRecycler("Old Town Scrap Traders", "Near KR Market, Bengaluru",
                 12.9634, 77.5770, (C, B), Decimal("10.00"), False),
    # --- Coverage additions: all active, CLOTHES and/or BOOKS only (still none takes TOYS). ---
    SeedRecycler("Yeshwanthpur Fibre Reclaim", "Tumkur Road, Yeshwanthpur Industrial Suburb, Bengaluru",
                 13.0230, 77.5420, (C,), Decimal("11.00"), True),
    SeedRecycler("Jalahalli Paper & Cloth Traders", "Jalahalli Cross, Bengaluru",
                 13.0510, 77.5380, (C, B), Decimal("9.00"), True),
    SeedRecycler("Rajajinagar Industrial Recyclers", "Rajajinagar Industrial Town, Bengaluru",
                 12.9930, 77.5470, (C, B), Decimal("9.50"), True),
    SeedRecycler("Hebbal Reuse Works", "Hebbal Industrial Area, Bengaluru",
                 13.0370, 77.5990, (C,), Decimal("10.50"), True),
    SeedRecycler("Yelahanka Paper Reclaim", "Yelahanka Industrial Area, Bengaluru",
                 13.1010, 77.5940, (B,), Decimal("8.00"), True),
    SeedRecycler("KR Puram Textile Yard", "Old Madras Road, KR Puram, Bengaluru",
                 13.0100, 77.7000, (C,), Decimal("11.50"), True),
    SeedRecycler("Whitefield Material Recovery Hub", "EPIP Zone, Whitefield, Bengaluru",
                 12.9760, 77.7480, (C, B), Decimal("10.00"), True),
    SeedRecycler("Marathahalli Scrap & Cloth Co.", "Marathahalli Industrial Area, Bengaluru",
                 12.9590, 77.6990, (C, B), Decimal("9.50"), True),
    SeedRecycler("Electronic City Recycling Park", "Hosur Road, Electronic City Phase 2, Bengaluru",
                 12.8470, 77.6650, (C, B), Decimal("12.50"), True),
    SeedRecycler("Bannerghatta Road Reclaim Depot", "Bannerghatta Main Road, Bengaluru",
                 12.8870, 77.5990, (B, C), Decimal("9.00"), True),
    SeedRecycler("Kengeri Industrial Recyclers", "Kengeri Industrial Area, Bengaluru",
                 12.9120, 77.4800, (C,), Decimal("10.00"), True),
    SeedRecycler("RR Nagar Material Recovery", "Rajarajeshwari Nagar Industrial Area, Bengaluru",
                 12.9250, 77.5170, (C, B), Decimal("9.75"), True),
)  # fmt: skip


@dataclass(frozen=True)
class SeedProvider:
    name: str
    base_fee: Decimal
    per_km_rate: Decimal
    is_active: bool


# Fictional couriers. Pricing is SIMULATED: base fee + per-km rate x distance.
LOGISTICS_PROVIDERS: tuple[SeedProvider, ...] = (
    SeedProvider("Swift Wheels Logistics", Decimal("40.00"), Decimal("12.00"), True),
    SeedProvider("UrbanHop Couriers", Decimal("30.00"), Decimal("15.00"), True),
    SeedProvider("GreenRoute Carriers", Decimal("50.00"), Decimal("9.00"), False),
)  # fmt: skip


@dataclass
class SeedReport:
    organisations_created: list[str] = field(default_factory=list)
    organisations_existing: list[str] = field(default_factory=list)
    recyclers_created: list[str] = field(default_factory=list)
    recyclers_existing: list[str] = field(default_factory=list)
    providers_created: list[str] = field(default_factory=list)
    providers_existing: list[str] = field(default_factory=list)
    donor_created: bool = False


def _registration_id(i: int) -> str:
    return f"SEED-BLR-{i:03d}"


def seed(db: Session, password: str) -> SeedReport:
    report = SeedReport()
    geocoder = PassthroughGeocoder()
    now = datetime.now(UTC)

    for i, s in enumerate(ORGANISATIONS, start=1):
        reg_id = _registration_id(i)
        if db.scalar(select(OrganizationProfile.id).where(OrganizationProfile.registration_id == reg_id)):
            report.organisations_existing.append(s.name)
            continue
        _, org = users.register_acceptor(
            db,
            AcceptorRegister(
                email=s.email,
                password=password,
                full_name=f"{s.name} (seed)",
                phone="+91 80 4000 0000",
                organization={
                    "name": s.name,
                    "registration_id": reg_id,
                    "contact_person": "Seed Contact",
                    "phone": "+91 80 4000 0000",
                    "address_text": s.address,
                    "latitude": s.lat,
                    "longitude": s.lng,
                    "pickup_capable": s.pickup_capable,
                    "storage_capacity": s.capacity,
                    "categories_accepted": list(s.categories),
                },
            ),
            geocoder,
        )
        org.verification_status = s.verification
        org.verification_note = "Seed data"
        org.verification_updated_at = now
        for category, quantity, urgency in s.needs:
            db.add(
                CurrentNeed(organization_id=org.id, category=category, quantity_needed=quantity, urgency=urgency)
            )
        db.commit()
        report.organisations_created.append(s.name)

    for r in RECYCLERS:
        if db.scalar(select(WasteCollector.id).where(WasteCollector.name == r.name)):
            report.recyclers_existing.append(r.name)
            continue
        db.add(
            WasteCollector(
                name=r.name,
                address_text=r.address,
                latitude=r.lat,
                longitude=r.lng,
                categories_accepted=list(r.categories),
                rate_per_kg=r.rate_per_kg,
                is_active=r.is_active,
            )
        )
        db.commit()
        report.recyclers_created.append(r.name)

    for p in LOGISTICS_PROVIDERS:
        if db.scalar(select(LogisticsProvider.id).where(LogisticsProvider.name == p.name)):
            report.providers_existing.append(p.name)
            continue
        db.add(
            LogisticsProvider(name=p.name, base_fee=p.base_fee, per_km_rate=p.per_km_rate, is_active=p.is_active)
        )
        db.commit()
        report.providers_created.append(p.name)

    if users.get_by_email(db, DEMO_DONOR_EMAIL) is None:
        users.register_donor(
            db,
            DonorRegister(
                email=DEMO_DONOR_EMAIL, password=password, full_name="Demo Donor", phone="+91 98450 00000"
            ),
        )
        report.donor_created = True
    return report
