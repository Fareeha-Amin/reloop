from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import Donation
from tests.api import helpers as h


def test_create_donation(client):
    headers = h.donor(client)
    body = h.create_donation(client, headers, quantity=8, is_priority=True)
    assert body["status"] == "LISTED"
    assert body["quantity"] == 8
    assert body["is_priority"] is True
    assert body["editable"] is True
    assert body["allowed_actions"] == ["CANCEL", "OFFER"]
    assert body["images"] == []


def test_list_shows_only_my_donations(client):
    mine, theirs = h.donor(client), h.donor(client)
    a = h.create_donation(client, mine)
    h.create_donation(client, theirs)
    listed = client.get("/donations", headers=mine).json()
    assert [d["id"] for d in listed] == [a["id"]]


def test_other_donor_gets_404_admin_can_read(client, db):
    owner, other = h.donor(client), h.donor(client)
    donation = h.create_donation(client, owner)
    path = f"/donations/{donation['id']}"
    assert client.get(path, headers=owner).status_code == 200
    assert client.get(path, headers=other).status_code == 404
    assert client.get(path, headers=h.admin(client, db)).status_code == 200


def test_edit_while_listed(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = client.patch(
        f"/donations/{donation['id']}",
        headers=headers,
        json={"quantity": 3, "condition": "NEW", "note": None},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["quantity"], body["condition"], body["note"]) == (3, "NEW", None)


def test_edit_pickup_window_is_validated_against_stored_values(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    # New end before the stored start.
    end = datetime.fromisoformat(donation["pickup_window_start"]) - timedelta(hours=1)
    resp = client.patch(
        f"/donations/{donation['id']}", headers=headers, json={"pickup_window_end": end.isoformat()}
    )
    assert resp.status_code == 422


def test_other_donor_cannot_edit_or_cancel(client):
    owner, other = h.donor(client), h.donor(client)
    donation = h.create_donation(client, owner)
    assert client.patch(f"/donations/{donation['id']}", headers=other, json={"quantity": 1}).status_code == 404
    assert client.post(f"/donations/{donation['id']}/cancel", headers=other).status_code == 404


def test_cancel_keeps_the_donation_and_freezes_it(client, db):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = client.post(f"/donations/{donation['id']}/cancel", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "CANCELLED"
    assert body["editable"] is False
    assert body["allowed_actions"] == []

    # Never hard-deleted.
    assert db.scalar(select(func.count()).select_from(Donation).where(Donation.id == donation["id"])) == 1

    # Terminal: cannot cancel again or edit.
    assert client.post(f"/donations/{donation['id']}/cancel", headers=headers).status_code == 409
    assert client.patch(f"/donations/{donation['id']}", headers=headers, json={"quantity": 1}).status_code == 409


def test_there_is_no_delete_route(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    assert client.delete(f"/donations/{donation['id']}", headers=headers).status_code == 405


def test_status_cannot_be_patched(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = client.patch(f"/donations/{donation['id']}", headers=headers, json={"status": "CANCELLED"})
    assert resp.status_code == 422


def test_window_in_the_past_rejected(client):
    headers = h.donor(client)
    start = datetime.now(UTC) - timedelta(days=2)
    resp = client.post(
        "/donations",
        headers=headers,
        json=h.donation_payload(
            pickup_window_start=start.isoformat(),
            pickup_window_end=(start + timedelta(hours=1)).isoformat(),
        ),
    )
    assert resp.status_code == 422


def test_admin_can_list_all_donations_and_filter_by_status(client, db):
    d1, d2 = h.donor(client), h.donor(client)
    a = h.create_donation(client, d1)
    b = h.create_donation(client, d2)
    client.post(f"/donations/{b['id']}/cancel", headers=d2)
    admin = h.admin(client, db)

    all_ids = {d["id"] for d in client.get("/admin/donations", headers=admin).json()}
    assert {a["id"], b["id"]} <= all_ids
    cancelled = client.get("/admin/donations?status=CANCELLED", headers=admin).json()
    assert [d["id"] for d in cancelled] == [b["id"]]


def test_pagination_bounds(client):
    headers = h.donor(client)
    assert client.get("/donations?limit=0", headers=headers).status_code == 422
    assert client.get("/donations?limit=101", headers=headers).status_code == 422
