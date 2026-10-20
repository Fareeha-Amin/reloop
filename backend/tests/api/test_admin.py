import pytest
from pydantic import ValidationError

from app.cli import create_admin
from app.services.errors import Conflict
from tests.api import helpers as h


def test_admin_lists_pending_and_verifies(client, db):
    _, body = h.acceptor(client)
    org_id = body["organization"]["id"]
    admin = h.admin(client, db)

    pending = client.get("/admin/organisations?verification_status=PENDING", headers=admin).json()
    assert org_id in {o["id"] for o in pending}

    resp = client.patch(
        f"/admin/organisations/{org_id}/verification",
        headers=admin,
        json={"status": "VERIFIED", "note": "Registration certificate checked"},
    )
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["verification_status"] == "VERIFIED"
    assert detail["verification_note"] == "Registration certificate checked"
    assert detail["verification_updated_at"] is not None
    assert detail["account_email"] == body["user"]["email"]

    pending = client.get("/admin/organisations?verification_status=PENDING", headers=admin).json()
    assert org_id not in {o["id"] for o in pending}


def test_verification_records_which_admin(client, db):
    from app.models import OrganizationProfile, User
    from sqlalchemy import select

    _, body = h.acceptor(client)
    admin = h.admin(client, db)
    admin_id = client.get("/auth/me", headers=admin).json()["id"]
    client.patch(
        f"/admin/organisations/{body['organization']['id']}/verification",
        headers=admin,
        json={"status": "REJECTED", "note": "Registration ID not found"},
    )
    org = db.scalar(select(OrganizationProfile).where(OrganizationProfile.id == body["organization"]["id"]))
    assert str(org.verification_updated_by_id) == admin_id
    assert db.get(User, org.verification_updated_by_id).role == "ADMIN"


def test_admin_detail_includes_needs(client, db):
    headers, body = h.acceptor(client)
    client.post(
        "/organisations/me/needs",
        headers=headers,
        json={"category": "CLOTHES", "quantity_needed": 30, "urgency": "HIGH"},
    )
    detail = client.get(f"/admin/organisations/{body['organization']['id']}", headers=h.admin(client, db)).json()
    assert [(n["category"], n["quantity_needed"]) for n in detail["needs"]] == [("CLOTHES", 30)]


def test_unknown_verification_status_rejected(client, db):
    _, body = h.acceptor(client)
    resp = client.patch(
        f"/admin/organisations/{body['organization']['id']}/verification",
        headers=h.admin(client, db),
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 422


def test_missing_organisation_is_404(client, db):
    import uuid

    resp = client.get(f"/admin/organisations/{uuid.uuid4()}", headers=h.admin(client, db))
    assert resp.status_code == 404


def test_cli_create_admin(db):
    user = create_admin(db, "Ops@Example.org", h.PASSWORD, "Ops")
    assert (user.email, user.role, user.phone) == ("ops@example.org", "ADMIN", None)
    with pytest.raises(Conflict):
        create_admin(db, "ops@example.org", h.PASSWORD, "Ops again")


def test_cli_create_admin_validates_input(db):
    with pytest.raises(ValidationError):
        create_admin(db, "not-an-email", h.PASSWORD, "Ops")
    with pytest.raises(ValidationError):
        create_admin(db, "ops2@example.org", "short", "Ops")
