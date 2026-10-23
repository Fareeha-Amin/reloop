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
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Category, Urgency, VerificationStatus
from app.models import CurrentNeed, OrganizationProfile, WasteCollector
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


# None accepts TOYS (deliberately).
RECYCLERS: tuple[SeedRecycler, ...] = (
    SeedRecycler("GreenCycle Textile Recovery", "Peenya Industrial Area, Bengaluru",
                 13.0285, 77.5197, (C,), Decimal("12.00"), True),
    SeedRecycler("PaperLoop Recyclers", "Bommanahalli, Hosur Road, Bengaluru",
                 12.9081, 77.6237, (B, C), Decimal("8.50"), True),
    SeedRecycler("Old Town Scrap Traders", "Near KR Market, Bengaluru",
                 12.9634, 77.5770, (C, B), Decimal("10.00"), False),
)  # fmt: skip


@dataclass
class SeedReport:
    organisations_created: list[str] = field(default_factory=list)
    organisations_existing: list[str] = field(default_factory=list)
    recyclers_created: list[str] = field(default_factory=list)
    recyclers_existing: list[str] = field(default_factory=list)
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

    if users.get_by_email(db, DEMO_DONOR_EMAIL) is None:
        users.register_donor(
            db,
            DonorRegister(
                email=DEMO_DONOR_EMAIL, password=password, full_name="Demo Donor", phone="+91 98450 00000"
            ),
        )
        report.donor_created = True
    return report
