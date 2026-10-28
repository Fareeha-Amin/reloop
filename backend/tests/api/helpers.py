"""Builders for API tests. Each returns ready-to-use auth headers."""

import io
import itertools
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.cli import create_admin

PASSWORD = "correct-horse-battery"
_counter = itertools.count()

# Central Bengaluru
LAT, LNG = 12.9716, 77.5946


def _unique(prefix: str) -> str:
    return f"{prefix}{next(_counter)}"


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def donor(client: TestClient) -> dict[str, str]:
    email = f"{_unique('donor')}@example.org"
    resp = client.post(
        "/auth/register/donor",
        json={"email": email, "password": PASSWORD, "full_name": "Asha Rao", "phone": "+91 98450 00000"},
    )
    assert resp.status_code == 201, resp.text
    return auth(login(client, email))


def organization_payload(**overrides) -> dict:
    payload = {
        "name": "Sunrise Children's Home",
        "registration_id": _unique("KA-NGO-"),
        "contact_person": "Meera Iyer",
        "phone": "+91 80 2222 3333",
        "address_text": "12 MG Road, Bengaluru",
        "latitude": LAT,
        "longitude": LNG,
        "pickup_capable": True,
        "storage_capacity": 200,
        "categories_accepted": ["CLOTHES", "BOOKS"],
    }
    payload.update(overrides)
    return payload


def acceptor(client: TestClient, **org_overrides) -> tuple[dict[str, str], dict]:
    """Returns (headers, registration response body)."""
    email = f"{_unique('acceptor')}@example.org"
    resp = client.post(
        "/auth/register/acceptor",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Meera Iyer",
            "phone": "+91 98450 11111",
            "organization": organization_payload(**org_overrides),
        },
    )
    assert resp.status_code == 201, resp.text
    return auth(login(client, email)), resp.json()


def admin(client: TestClient, db: Session) -> dict[str, str]:
    email = f"{_unique('admin')}@example.org"
    create_admin(db, email, PASSWORD, "Platform Admin")
    return auth(login(client, email))


def donation_payload(**overrides) -> dict:
    start = datetime.now(UTC) + timedelta(days=1)
    payload = {
        "category": "CLOTHES",
        "quantity": 12,
        "condition": "GENTLY_USED",
        "note": "Children's winter clothes, ages 4-8",
        "is_priority": False,
        "pickup_address_text": "45 Indiranagar 100ft Rd, Bengaluru",
        "pickup_latitude": 12.9784,
        "pickup_longitude": 77.6408,
        "pickup_window_start": start.isoformat(),
        "pickup_window_end": (start + timedelta(hours=3)).isoformat(),
    }
    payload.update(overrides)
    return payload


def create_donation(client: TestClient, headers: dict, **overrides) -> dict:
    resp = client.post("/donations", json=donation_payload(**overrides), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def window(start_in: timedelta = timedelta(days=1), length: timedelta = timedelta(days=9)) -> dict:
    """A pickup window. The default is long enough to outlast an offer's TTL."""
    start = datetime.now(UTC) + start_in
    return {
        "pickup_window_start": start.isoformat(),
        "pickup_window_end": (start + length).isoformat(),
    }


# Bengaluru places, relative to the donor's default pickup point (Indiranagar).
INDIRANAGAR = (12.9784, 77.6408)
NEAR = (12.9719, 77.6412)  # ~0.7 km
KORAMANGALA = (12.9352, 77.6245)  # ~5 km
HSR = (12.9116, 77.6474)  # ~7.5 km
MALLESHWARAM = (13.0035, 77.5710)  # ~8 km
YELAHANKA = (13.1155, 77.5960)  # ~16 km: outside 15 km, inside the radius after one decline
NELAMANGALA = (13.0977, 77.3910)  # ~30 km: outside every radius
PEENYA = (13.0285, 77.5197)  # ~16 km from Nelamangala


def verified_acceptor(client: TestClient, db: Session, at=NEAR, **org_overrides) -> tuple[dict[str, str], str]:
    """A VERIFIED organisation at `at`. Returns (headers, organisation id)."""
    from app.constants import VerificationStatus
    from app.models import OrganizationProfile

    headers, body = acceptor(client, latitude=at[0], longitude=at[1], **org_overrides)
    org_id = body["organization"]["id"]
    db.get(OrganizationProfile, org_id).verification_status = VerificationStatus.VERIFIED
    db.commit()
    return headers, org_id


def add_need(client: TestClient, headers: dict, category="CLOTHES", quantity=20, urgency="HIGH") -> None:
    resp = client.post(
        "/organisations/me/needs",
        headers=headers,
        json={"category": category, "quantity_needed": quantity, "urgency": urgency},
    )
    assert resp.status_code == 201, resp.text


def offer(client: TestClient, donor_headers: dict, donation_id: str, organization_id: str | None = None) -> dict:
    body = {"organization_id": organization_id} if organization_id else None
    resp = client.post(f"/donations/{donation_id}/offer", headers=donor_headers, json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def inbox(client: TestClient, headers: dict) -> list[dict]:
    resp = client.get("/organisations/me/offers", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def the_offer(client: TestClient, headers: dict, donation_id: str) -> dict:
    """This organisation's open offer for the donation."""
    matches = [o for o in inbox(client, headers) if o["donation_id"] == donation_id]
    assert len(matches) == 1, f"expected one open offer, inbox: {inbox(client, headers)}"
    return matches[0]


def reject(client: TestClient, headers: dict, donation_id: str, reason_code: str = "NOT_NEEDED") -> dict:
    match_id = the_offer(client, headers, donation_id)["match_id"]
    resp = client.post(
        f"/organisations/me/offers/{match_id}/reject", headers=headers, json={"reason_code": reason_code}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def accept(client: TestClient, headers: dict, donation_id: str) -> dict:
    match_id = the_offer(client, headers, donation_id)["match_id"]
    resp = client.post(f"/organisations/me/offers/{match_id}/accept", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def choose_acceptor_collection(client: TestClient, donor_headers: dict, donation_id: str) -> dict:
    """The donor's choice that a pickup-capable organisation collects: unlocks that
    organisation's own schedule-pickup action."""
    resp = client.post(f"/donations/{donation_id}/choose-acceptor-collection", headers=donor_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def status(client: TestClient, donor_headers: dict, donation_id: str) -> dict:
    resp = client.get(f"/donations/{donation_id}", headers=donor_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def add_recycler(db: Session, name: str, at=PEENYA, categories=("CLOTHES",), rate="12.00", active=True):
    from decimal import Decimal

    from app.models import WasteCollector

    collector = WasteCollector(
        name=name,
        address_text="Industrial Area, Bengaluru",
        latitude=at[0],
        longitude=at[1],
        categories_accepted=list(categories),
        rate_per_kg=Decimal(rate),
        is_active=active,
    )
    db.add(collector)
    db.commit()
    return collector


def add_provider(db: Session, name: str = "Test Couriers", base_fee="30.00", per_km_rate="10.00", active=True):
    from decimal import Decimal

    from app.models import LogisticsProvider

    provider = LogisticsProvider(
        name=name, base_fee=Decimal(base_fee), per_km_rate=Decimal(per_km_rate), is_active=active
    )
    db.add(provider)
    db.commit()
    return provider


def image_bytes(fmt: str = "JPEG", size=(32, 24), color=(200, 30, 30), **save_kwargs) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()
