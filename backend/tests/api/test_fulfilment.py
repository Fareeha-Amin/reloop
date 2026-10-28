"""Acceptance, address privacy, the handover and completion."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import AddressAccessEvent, Match
from tests.api import helpers as h

ADDRESS_KEYS = {"pickup_address_text", "pickup_latitude", "pickup_longitude"}


def _matched(client, db, **org):
    """A donor, a verified organisation and a donation offered to it."""
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db, **org)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    return donor, org_headers, org_id, donation


def test_before_acceptance_an_acceptor_sees_no_address(client, db):
    _, org_headers, _, donation = _matched(client, db, at=h.KORAMANGALA)
    offer = h.the_offer(client, org_headers, donation["id"])
    assert not ADDRESS_KEYS & set(offer)
    assert offer["distance_km"] == 5.0  # rounded to 0.5 km
    assert offer["allowed_actions"] == ["ACCEPT", "REJECT"]
    # The full donation endpoint is not open to acceptors at all.
    assert client.get(f"/donations/{donation['id']}", headers=org_headers).status_code == 403


def test_images_are_visible_to_the_offered_organisation_only(client, db):
    donor = h.donor(client)
    offered, _ = h.verified_acceptor(client, db, at=h.NEAR)  # nearer: the top candidate
    outsider, _ = h.verified_acceptor(client, db, at=h.MALLESHWARAM)
    donation = h.create_donation(client, donor, **h.window())
    image = client.post(
        f"/donations/{donation['id']}/images",
        headers=donor,
        files=[("files", ("a.jpg", h.image_bytes(), "image/jpeg"))],
    ).json()[0]
    path = f"/donations/{donation['id']}/images/{image['id']}"
    assert client.get(path, headers=offered).status_code == 404  # nothing offered yet

    h.offer(client, donor, donation["id"])
    assert h.the_offer(client, offered, donation["id"])["image_ids"] == [image["id"]]
    assert client.get(path, headers=offered).status_code == 200
    assert client.get(path, headers=outsider).status_code == 404
    # Once offered, the donation is no longer editable: no more images.
    more = client.post(
        f"/donations/{donation['id']}/images", headers=donor, files=[("files", ("b.jpg", h.image_bytes(), "image/jpeg"))]
    )
    assert more.status_code == 409


def test_accept_releases_the_address_and_records_the_release(client, db):
    donor, org_headers, org_id, donation = _matched(client, db)
    body = h.accept(client, org_headers, donation["id"])
    assert body["status"] == "ACCEPTED" and body["address_released"] is True
    assert body["pickup_address_text"] == "45 Indiranagar 100ft Rd, Bengaluru"
    # No schedule action yet: the donor hasn't chosen a path.
    assert body["allowed_actions"] == []
    assert body["awaiting_donor_handover_choice"] is True

    events = list(db.scalars(select(AddressAccessEvent).where(AddressAccessEvent.donation_id == donation["id"])))
    assert [(e.kind, str(e.organization_id)) for e in events] == [("RELEASED_TO_ACCEPTOR", org_id)]

    # The donor sees all three handover choices (no provider seeded, so no BOOK_PICKUP).
    assert h.status(client, donor, donation["id"])["allowed_actions"] == ["CHOOSE_ACCEPTOR_COLLECTION", "CHOOSE_DROPOFF"]


def test_answering_twice_is_refused(client, db):
    _, org_headers, _, donation = _matched(client, db)
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]
    assert client.post(f"/organisations/me/offers/{match_id}/accept", headers=org_headers).status_code == 200
    assert client.post(f"/organisations/me/offers/{match_id}/accept", headers=org_headers).status_code == 409
    resp = client.post(
        f"/organisations/me/offers/{match_id}/reject", headers=org_headers, json={"reason_code": "OTHER"}
    )
    assert resp.status_code == 409


def test_another_organisation_cannot_see_or_answer_the_offer(client, db):
    _, org_headers, _, donation = _matched(client, db)
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]
    other, _ = h.verified_acceptor(client, db, at=h.NELAMANGALA)
    assert client.get(f"/organisations/me/offers/{match_id}", headers=other).status_code == 404
    assert client.post(f"/organisations/me/offers/{match_id}/accept", headers=other).status_code == 404


def test_acceptor_pickup_path_to_completed(client, db):
    donor, org_headers, _, donation = _matched(client, db)
    h.accept(client, org_headers, donation["id"])
    end = datetime.fromisoformat(donation["pickup_window_end"])
    path = f"/organisations/me/donations/{donation['id']}"

    # Not yet offered to the organisation: the donor hasn't chosen this path.
    resp = client.post(f"{path}/schedule-pickup", headers=org_headers, json={"scheduled_for": end.isoformat()})
    assert resp.status_code == 409

    chosen = h.choose_acceptor_collection(client, donor, donation["id"])
    assert chosen["allowed_actions"] == []  # already chosen; nothing left for the donor to press
    assert chosen["handover_options"] == [{"path": "ACCEPTOR_PICKUP", "available": True, "you_do_it": False}]
    assert client.get(path, headers=org_headers).json()["allowed_actions"] == ["SCHEDULE_PICKUP"]

    past = datetime.now(UTC) - timedelta(minutes=1)
    resp = client.post(f"{path}/schedule-pickup", headers=org_headers, json={"scheduled_for": past.isoformat()})
    assert resp.status_code == 422
    # The window is advisory: a pickup after it ends is accepted.
    resp = client.post(
        f"{path}/schedule-pickup", headers=org_headers, json={"scheduled_for": (end + timedelta(days=1)).isoformat()}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["handover"]["mode"] == "ACCEPTOR_PICKUP"
    assert resp.json()["allowed_actions"] == ["CONFIRM_RECEIPT"]

    body = client.post(f"/donations/{donation['id']}/mark-handed-over", headers=donor).json()
    assert body["status"] == "IN_TRANSIT"

    resp = client.post(f"{path}/confirm-receipt", headers=org_headers)
    assert resp.status_code == 200, resp.text
    done = resp.json()
    assert done["status"] == "COMPLETED"
    # The address was released until completion, and no longer.
    assert done["address_released"] is False and done["pickup_address_text"] is None
    assert h.status(client, donor, donation["id"])["allowed_actions"] == []


def test_donor_dropoff_path_and_receipt_straight_from_scheduled(client, db):
    donor, org_headers, _, donation = _matched(client, db, pickup_capable=False)
    h.accept(client, org_headers, donation["id"])
    path = f"/organisations/me/donations/{donation['id']}"
    assert client.get(path, headers=org_headers).json()["allowed_actions"] == []  # does not collect
    start = datetime.fromisoformat(donation["pickup_window_start"])
    resp = client.post(
        f"{path}/schedule-pickup", headers=org_headers, json={"scheduled_for": (start + timedelta(hours=1)).isoformat()}
    )
    assert resp.status_code == 409

    past = datetime.now(UTC) - timedelta(minutes=1)
    resp = client.post(f"/donations/{donation['id']}/choose-dropoff", headers=donor, json={"scheduled_for": past.isoformat()})
    assert resp.status_code == 422
    resp = client.post(
        f"/donations/{donation['id']}/choose-dropoff", headers=donor, json={"scheduled_for": (start - timedelta(hours=1)).isoformat()}
    )
    assert resp.status_code == 200, resp.text  # only "in the future" is required
    assert resp.json()["status"] == "PICKUP_SCHEDULED"

    done = client.post(f"{path}/confirm-receipt", headers=org_headers).json()
    assert done["status"] == "COMPLETED"
    assert done["handover"]["mode"] == "DONOR_DROPOFF"


def test_cancel_while_matched_retracts_the_offer(client, db):
    donor, org_headers, _, donation = _matched(client, db)
    resp = client.post(f"/donations/{donation['id']}/cancel", headers=donor)
    assert resp.status_code == 200 and resp.json()["status"] == "CANCELLED"
    match = db.scalar(select(Match).where(Match.donation_id == donation["id"]))
    assert match.response == "RETRACTED" and match.responder_id is None
    assert h.inbox(client, org_headers) == []


def test_donor_cannot_cancel_after_acceptance(client, db):
    donor, org_headers, _, donation = _matched(client, db)
    h.accept(client, org_headers, donation["id"])
    assert client.post(f"/donations/{donation['id']}/cancel", headers=donor).status_code == 409


def test_capacity_is_derived_from_held_donations(client, db):
    org_headers, org_id = h.verified_acceptor(client, db, storage_capacity=15)
    donor = h.donor(client)
    first = h.create_donation(client, donor, quantity=12, **h.window())
    h.offer(client, donor, first["id"])
    h.accept(client, org_headers, first["id"])

    second = h.create_donation(client, donor, quantity=5, **h.window())
    slate = client.get(f"/donations/{second['id']}/candidates", headers=donor).json()
    assert slate["candidates"] == [] and slate["filtered_out"] == {"INSUFFICIENT_CAPACITY": 1}

    # Completing the first frees the room: nothing was decremented, so nothing to restore.
    client.post(f"/donations/{first['id']}/choose-dropoff", headers=donor,
                json={"scheduled_for": first["pickup_window_start"]})
    client.post(f"/organisations/me/donations/{first['id']}/confirm-receipt", headers=org_headers)
    slate = client.get(f"/donations/{second['id']}/candidates", headers=donor).json()
    assert [c["organization_id"] for c in slate["candidates"]] == [org_id]


def test_accepted_list_shows_only_current_acceptances(client, db):
    _, org_headers, _, donation = _matched(client, db)
    assert client.get("/organisations/me/donations", headers=org_headers).json() == []
    h.accept(client, org_headers, donation["id"])
    listed = client.get("/organisations/me/donations", headers=org_headers).json()
    assert [d["donation_id"] for d in listed] == [donation["id"]]
