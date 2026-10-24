"""The public discovery map: verified organisations only, at approximate positions,
without addresses or contact details."""

from app.constants import VerificationStatus
from app.models import OrganizationProfile
from tests.api import helpers as h


def _discover(client, **params) -> dict:
    resp = client.get("/discovery/organisations", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _by_id(body: dict) -> dict[str, dict]:
    return {o["id"]: o for o in body["organisations"]}


def test_public_and_lists_verified_organisations_only(client, db):
    _, verified = h.verified_acceptor(client, db, name="Verified Home")
    _, pending = h.acceptor(client, name="Pending Home")
    _, rejected = h.acceptor(client, name="Rejected Home")
    db.get(OrganizationProfile, rejected["organization"]["id"]).verification_status = VerificationStatus.REJECTED
    db.commit()

    body = _discover(client)  # no Authorization header
    found = _by_id(body)
    assert verified in found
    assert pending["organization"]["id"] not in found
    assert rejected["organization"]["id"] not in found


def test_positions_are_rounded_and_no_contact_details_are_shown(client, db):
    _, org_id = h.verified_acceptor(client, db, at=(12.97194, 77.64126))

    body = _discover(client)
    org = _by_id(body)[org_id]
    assert (org["latitude"], org["longitude"]) == (12.97, 77.64)
    assert body["positions_are_approximate"] is True
    assert body["position_error_km"] == 0.8
    assert set(org) == {"id", "name", "latitude", "longitude", "pickup_capable", "categories_accepted", "needs"}


def test_category_filter(client, db):
    _, books = h.verified_acceptor(client, db, categories_accepted=["BOOKS"])
    _, clothes = h.verified_acceptor(client, db, categories_accepted=["CLOTHES", "TOYS"])

    found = _by_id(_discover(client, category="TOYS"))
    assert clothes in found and books not in found
    assert client.get("/discovery/organisations", params={"category": "FOOD"}).status_code == 422


def test_only_active_needs_are_shown(client, db):
    headers, org_id = h.verified_acceptor(client, db)
    h.add_need(client, headers, category="CLOTHES", quantity=40, urgency="HIGH")
    h.add_need(client, headers, category="BOOKS", quantity=10, urgency="LOW")
    books = next(n for n in client.get("/organisations/me/needs", headers=headers).json() if n["category"] == "BOOKS")
    resp = client.patch(f"/organisations/me/needs/{books['id']}", headers=headers, json={"is_active": False})
    assert resp.status_code == 200, resp.text

    needs = _by_id(_discover(client))[org_id]["needs"]
    assert needs == [{"category": "CLOTHES", "quantity_needed": 40, "urgency": "HIGH"}]
