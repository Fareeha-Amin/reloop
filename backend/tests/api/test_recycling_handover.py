"""The recycling handover step: a donor's own drop-off or platform pickup to the
assigned recycler, required before an admin can confirm recycled (there is no recycler
login to confirm receipt any other way)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.constants import STALL_TIMEOUTS, DonationStatus
from app.services import sweeper
from tests.api import helpers as h


def _escalated(client, db, category="CLOTHES"):
    """A donation far from every organisation, escalated for want of candidates."""
    donor = h.donor(client)
    h.verified_acceptor(client, db, at=h.NEAR, categories_accepted=["CLOTHES", "TOYS", "BOOKS"])
    donation = h.create_donation(
        client, donor, category=category, pickup_latitude=h.NELAMANGALA[0], pickup_longitude=h.NELAMANGALA[1],
        **h.window(),
    )
    assert h.offer(client, donor, donation["id"])["status"] == "ESCALATED"
    return donor, donation


def _redirected(client, db, category="CLOTHES"):
    donor, donation = _escalated(client, db, category=category)
    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    assert resp.status_code == 200 and resp.json()["status"] == "WASTE_REDIRECTED", resp.text
    return donor, donation


def test_deliver_to_recycler_then_confirm(client, db):
    h.add_recycler(db, "Drop Zone", at=h.PEENYA)
    donor, donation = _redirected(client, db)
    admin = h.admin(client, db)

    resp = client.post(f"/donations/{donation['id']}/deliver-to-recycler", headers=donor)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "RECYCLING_IN_TRANSIT"
    assert body["allowed_actions"] == []  # the donor has nothing left to press

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    rec = timeline["recyclings"][0]
    assert rec["collector_name"] == "Drop Zone"
    assert rec["handover"]["mode"] == "DONOR_DROPOFF"
    assert rec["settlement"] is None  # not yet confirmed

    resp = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "Dropped off"}
    )
    assert resp.status_code == 200 and resp.json()["status"] == "RECYCLED", resp.text


def test_confirm_recycled_is_unavailable_before_the_handover(client, db):
    h.add_recycler(db, "Drop Zone", at=h.PEENYA)
    donor, donation = _redirected(client, db)
    admin = h.admin(client, db)

    resp = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "too soon"}
    )
    assert resp.status_code == 409
    # WASTE_REDIRECTED itself needs no admin action yet, so it is in neither queue.
    queue_ids = {i["donation"]["id"] for i in client.get("/admin/queue", headers=admin).json()}
    awaiting_ids = {i["donation"]["id"] for i in client.get("/admin/awaiting", headers=admin).json()}
    assert donation["id"] not in queue_ids
    assert donation["id"] not in awaiting_ids


def test_platform_pickup_to_recycler(client, db):
    h.add_recycler(db, "Far Recycler", at=h.PEENYA)
    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    donor, donation = _redirected(client, db)

    quote = client.get(f"/donations/{donation['id']}/recycler-pickup-quote", headers=donor)
    assert quote.status_code == 200, quote.text
    q = quote.json()
    assert q["wallet_balance"] == "0.00"
    assert [p["provider_name"] for p in q["providers"]] == ["Swift"]
    cost = next(p["cost"] for p in q["providers"])

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/donations/{donation['id']}/book-recycler-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": future, "wallet_amount": "0"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "RECYCLING_SCHEDULED"

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    booking = timeline["bookings"][0]
    assert Decimal(booking["cost"]) == Decimal(cost)
    assert booking["status"] == "BOOKED"
    assert booking["payment"]["status"] == "SUCCEEDED"

    admin = h.admin(client, db)
    ledger_before = Decimal(client.get("/admin/commission", headers=admin).json()["total"])
    assert ledger_before > 0  # the booking's own commission is already on the ledger

    # The donor hands the goods to the courier; only then is the booking picked up.
    handed = client.post(f"/donations/{donation['id']}/mark-recycler-handed-over", headers=donor)
    assert handed.status_code == 200, handed.text
    assert handed.json()["status"] == "RECYCLING_IN_TRANSIT"
    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert timeline["bookings"][0]["status"] == "PICKED_UP"

    resp = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "Courier delivered"}
    )
    assert resp.status_code == 200 and resp.json()["status"] == "RECYCLED", resp.text
    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert timeline["bookings"][0]["status"] == "DELIVERED"


def test_after_booking_the_donor_can_hand_over_and_admin_confirm_waits_for_it(client, db):
    """The donation-pickup split, mirrored: booking alone (RECYCLING_SCHEDULED) offers the
    donor the handed-over action, and refuses admin confirmation until it is recorded."""
    h.add_recycler(db, "Far Recycler", at=h.PEENYA)
    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    donor, donation = _redirected(client, db)
    admin = h.admin(client, db)

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    booked = client.post(
        f"/donations/{donation['id']}/book-recycler-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": future, "wallet_amount": "0"},
    )
    assert booked.status_code == 200, booked.text
    assert booked.json()["status"] == "RECYCLING_SCHEDULED"
    assert booked.json()["allowed_actions"] == ["MARK_RECYCLER_HANDED_OVER"]

    refused = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "too soon"}
    )
    assert refused.status_code == 409
    assert "RECYCLING_SCHEDULED" in refused.json()["detail"]

    handed = client.post(f"/donations/{donation['id']}/mark-recycler-handed-over", headers=donor)
    assert handed.status_code == 200, handed.text
    assert handed.json()["allowed_actions"] == []
    assert client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "now"}
    ).status_code == 200


def test_a_stalled_recycler_pickup_is_cancelled_and_refunded(client, db):
    h.add_recycler(db, "Far Recycler", at=h.PEENYA)
    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    donor, donation = _redirected(client, db)
    admin = h.admin(client, db)
    commission_before = Decimal(client.get("/admin/commission", headers=admin).json()["total"])

    scheduled_for = datetime.now(UTC) + timedelta(days=1)
    resp = client.post(
        f"/donations/{donation['id']}/book-recycler-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": scheduled_for.isoformat(), "wallet_amount": "0"},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(client.get("/admin/commission", headers=admin).json()["total"]) > commission_before

    # Booked but never handed over: stalls after RECYCLING_SCHEDULED's own timeout.
    report = sweeper.sweep(db, datetime.now(UTC) + STALL_TIMEOUTS[DonationStatus.RECYCLING_SCHEDULED])
    applied = [(i.from_state, i.action, i.to_state) for i in report.applied]
    assert ("RECYCLING_SCHEDULED", "STALL", "NEEDS_ADMIN") in applied

    status = h.status(client, donor, donation["id"])
    assert status["status"] == "NEEDS_ADMIN"

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    booking = timeline["bookings"][0]
    assert booking["status"] == "CANCELLED"
    assert booking["cancel_reason"]
    assert booking["payment"]["status"] == "REFUNDED"

    commission_after = Decimal(client.get("/admin/commission", headers=admin).json()["total"])
    assert commission_after == commission_before


def test_recycling_never_reaches_an_organisations_inbox_or_capacity(client, db):
    """Recycling never holds an organisation's slot: no Match, no address release, no
    chat, no capacity change, whatever handover path the donor takes."""
    h.add_recycler(db, "Drop Zone", at=h.PEENYA)
    org_headers, _ = h.verified_acceptor(client, db, at=h.NEAR, categories_accepted=["CLOTHES"])
    donor, donation = _redirected(client, db)

    resp = client.post(f"/donations/{donation['id']}/deliver-to-recycler", headers=donor)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["holder"] is None
    assert body["chat"] is None

    assert h.inbox(client, org_headers) == []

    admin = h.admin(client, db)
    resp = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin, json={"reason": "test"}
    )
    assert resp.status_code == 200 and resp.json()["status"] == "RECYCLED", resp.text
    final = client.get(f"/donations/{donation['id']}", headers=donor).json()
    assert final["holder"] is None and final["chat"] is None
