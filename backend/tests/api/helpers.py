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


def image_bytes(fmt: str = "JPEG", size=(32, 24), color=(200, 30, 30), **save_kwargs) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()
