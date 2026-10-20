from sqlalchemy import select

from app.models import OrganizationProfile, User
from tests.api import helpers as h


def test_acceptor_registration_creates_user_and_unverified_organisation(client, db):
    headers, body = h.acceptor(client, categories_accepted=["TOYS", "BOOKS"])
    assert body["user"]["role"] == "ACCEPTOR"
    org = body["organization"]
    assert org["verification_status"] == "PENDING"
    assert org["categories_accepted"] == ["TOYS", "BOOKS"]
    assert org["verification_updated_at"] is None

    mine = client.get("/organisations/me", headers=headers).json()
    assert mine["id"] == org["id"]

    stored = db.scalar(select(OrganizationProfile).where(OrganizationProfile.id == org["id"]))
    assert stored.user.email == body["user"]["email"]


def test_registration_is_atomic_when_registration_id_is_taken(client, db):
    _, first = h.acceptor(client)
    reg_id = first["organization"]["registration_id"]
    resp = client.post(
        "/auth/register/acceptor",
        json={
            "email": "second@example.org",
            "password": h.PASSWORD,
            "full_name": "Second",
            "phone": "+91 98450 22222",
            "organization": h.organization_payload(registration_id=reg_id),
        },
    )
    assert resp.status_code == 409
    assert db.scalar(select(User).where(User.email == "second@example.org")) is None


def test_registration_needs_valid_coordinates(client):
    resp = client.post(
        "/auth/register/acceptor",
        json={
            "email": "badgeo@example.org",
            "password": h.PASSWORD,
            "full_name": "B",
            "phone": "+91 98450 22222",
            "organization": h.organization_payload(latitude=123.0),
        },
    )
    assert resp.status_code == 422


def test_acceptor_can_update_operational_fields(client):
    headers, _ = h.acceptor(client)
    resp = client.patch(
        "/organisations/me",
        headers=headers,
        json={
            "storage_capacity": 50,
            "pickup_capable": False,
            "address_text": "7 Jayanagar 4th Block",
            "latitude": 12.925,
            "longitude": 77.5838,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["storage_capacity"], body["pickup_capable"]) == (50, False)
    assert (body["address_text"], body["latitude"]) == ("7 Jayanagar 4th Block", 12.925)


def test_acceptor_cannot_change_identity_or_verification(client):
    headers, _ = h.acceptor(client)
    for field, value in [("name", "Other"), ("registration_id", "X"), ("verification_status", "VERIFIED")]:
        assert client.patch("/organisations/me", headers=headers, json={field: value}).status_code == 422


def test_cannot_drop_a_category_that_has_an_active_need(client):
    headers, _ = h.acceptor(client, categories_accepted=["CLOTHES", "BOOKS"])
    client.post(
        "/organisations/me/needs",
        headers=headers,
        json={"category": "BOOKS", "quantity_needed": 10, "urgency": "HIGH"},
    )
    resp = client.patch("/organisations/me", headers=headers, json={"categories_accepted": ["CLOTHES"]})
    assert resp.status_code == 409
    assert "BOOKS" in resp.json()["detail"]
