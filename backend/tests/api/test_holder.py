"""The holding organisation's address and contact, shown to the donor while it holds the
donation (ACCEPTED, PICKUP_SCHEDULED, IN_TRANSIT), whatever the handover mode."""

from datetime import UTC, datetime, timedelta

from tests.api import helpers as h


def _future() -> str:
    return (datetime.now(UTC) + timedelta(days=2)).isoformat()


def _accepted(client, db, **org_overrides):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db, **org_overrides)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], org_id)
    assert h.status(client, donor, donation["id"])["holder"] is None  # MATCHED: not held
    h.accept(client, org_headers, donation["id"])
    return donor, org_headers, org_id, donation["id"]


def test_no_holder_before_acceptance(client, db):
    donor = h.donor(client)
    donation = h.create_donation(client, donor)
    assert donation["holder"] is None


def test_holder_address_and_contact_shown_while_held_with_acceptor_pickup(client, db):
    donor, org_headers, org_id, donation_id = _accepted(client, db)

    holder = h.status(client, donor, donation_id)["holder"]
    assert holder["organization_id"] == org_id
    assert holder["organization_name"] == "Sunrise Children's Home"
    assert holder["address_text"] == "12 MG Road, Bengaluru"
    assert holder["phone"] == "+91 80 2222 3333"
    assert holder["contact_person"] == "Meera Iyer"
    assert (holder["latitude"], holder["longitude"]) == h.NEAR
    assert holder["pickup_capable"] is True
    assert holder["handover"] is None

    h.choose_acceptor_collection(client, donor, donation_id)
    resp = client.post(
        f"/organisations/me/donations/{donation_id}/schedule-pickup",
        headers=org_headers,
        json={"scheduled_for": _future()},
    )
    assert resp.status_code == 200, resp.text
    holder = h.status(client, donor, donation_id)["holder"]
    assert holder["handover"]["mode"] == "ACCEPTOR_PICKUP"
    assert holder["address_text"] == "12 MG Road, Bengaluru"  # no exception for pickup

    resp = client.post(f"/donations/{donation_id}/mark-handed-over", headers=donor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["holder"]["phone"] == "+91 80 2222 3333"  # IN_TRANSIT: still held


def test_holder_with_donor_dropoff_and_gone_once_completed(client, db):
    donor, org_headers, _, donation_id = _accepted(client, db, pickup_capable=False)

    resp = client.post(
        f"/donations/{donation_id}/choose-dropoff", headers=donor, json={"scheduled_for": _future()}
    )
    assert resp.status_code == 200, resp.text
    holder = resp.json()["holder"]
    assert holder["handover"]["mode"] == "DONOR_DROPOFF"
    assert holder["address_text"] == "12 MG Road, Bengaluru"

    resp = client.post(f"/organisations/me/donations/{donation_id}/confirm-receipt", headers=org_headers)
    assert resp.status_code == 200, resp.text
    completed = h.status(client, donor, donation_id)
    assert completed["status"] == "COMPLETED"
    assert completed["holder"] is None


def test_admin_detail_includes_the_holder(client, db):
    _, _, org_id, donation_id = _accepted(client, db)
    admin = h.admin(client, db)
    resp = client.get(f"/admin/donations/{donation_id}", headers=admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["donation"]["holder"]["organization_id"] == org_id


def test_donor_list_includes_the_holder(client, db):
    donor, _, org_id, donation_id = _accepted(client, db)
    listed = {d["id"]: d for d in client.get("/donations", headers=donor).json()}
    assert listed[donation_id]["holder"]["organization_id"] == org_id
