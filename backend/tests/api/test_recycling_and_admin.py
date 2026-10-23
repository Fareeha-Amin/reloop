"""The recycling fallback, the admin queue, admin actions and address-access logging."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.constants import STALL_TIMEOUTS, DonationStatus
from app.models import AddressAccessEvent, Recycling, StatusEvent
from app.services import sweeper
from tests.api import helpers as h

FAR_LAT, FAR_LNG = h.NELAMANGALA


def _escalated(client, db, category="CLOTHES"):
    """A donation far from every organisation, escalated for want of candidates."""
    donor = h.donor(client)
    h.verified_acceptor(client, db, at=h.NEAR, categories_accepted=["CLOTHES", "TOYS", "BOOKS"])
    donation = h.create_donation(
        client, donor, category=category, pickup_latitude=FAR_LAT, pickup_longitude=FAR_LNG, **h.window()
    )
    assert h.offer(client, donor, donation["id"])["status"] == "ESCALATED"
    return donor, donation


def test_recycling_path_to_recycled_with_a_simulated_settlement(client, db):
    h.add_recycler(db, "Peenya Textiles", at=h.PEENYA, rate="12.00")
    h.add_recycler(db, "Closed Yard", at=h.NELAMANGALA, active=False)  # nearer, but inactive
    donor, donation = _escalated(client, db)

    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "WASTE_REDIRECTED"

    admin = h.admin(client, db)
    path = f"/admin/donations/{donation['id']}/confirm-recycled"
    assert client.post(path, headers=admin, json={}).status_code == 422  # a reason is required
    assert client.post(path, headers=admin, json={"reason": "  "}).status_code == 422
    resp = client.post(path, headers=admin, json={"reason": "Recycler confirmed collection by phone"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "RECYCLED"

    recycling = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()["recyclings"]
    assert len(recycling) == 1
    r = recycling[0]
    assert r["collector_name"] == "Peenya Textiles"
    assert (r["simulated"], r["mass_is_estimate"], r["weights_are_placeholders"]) == (True, True, True)
    s = r["settlement"]
    # 12 items x 0.5 kg x INR 12.00/kg = 72.00; fee 10% = 7.20; donor credit 64.80
    assert (s["estimated_mass_kg"], s["gross_value"], s["platform_fee"], s["donor_credit"]) == (
        "6.000", "72.00", "7.20", "64.80"
    )
    assert r["currency"] == "INR"


def test_toys_with_no_recycler_land_in_the_admin_queue(client, db):
    h.add_recycler(db, "Peenya Textiles", at=h.PEENYA, categories=("CLOTHES", "BOOKS"))
    donor, donation = _escalated(client, db, category="TOYS")

    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "NEEDS_ADMIN"
    actions = [
        e.action
        for e in db.scalars(select(StatusEvent).where(StatusEvent.donation_id == donation["id"]).order_by(StatusEvent.id))
    ]
    assert actions == ["ESCALATE", "REDIRECT_TO_RECYCLING", "NO_RECYCLER"]

    admin = h.admin(client, db)
    queue = client.get("/admin/queue", headers=admin).json()
    item = next(i for i in queue if i["donation"]["id"] == donation["id"])
    assert (item["from_state"], item["via"]) == ("WASTE_REDIRECTED", "NO_RECYCLER")
    assert "pickup_address_text" not in item["donation"]
    # Nothing to requeue to and nowhere to recycle: only cancelling is offered.
    assert item["allowed_actions"] == ["CANCEL"]
    base = f"/admin/donations/{donation['id']}"
    assert client.post(f"{base}/requeue", headers=admin, json={"reason": "try again"}).status_code == 409
    assert client.post(f"{base}/redirect-to-recycling", headers=admin, json={"reason": "x"}).status_code == 409

    resp = client.post(f"{base}/cancel", headers=admin, json={"reason": "No toy recycler in the city; donor informed"})
    assert resp.status_code == 200 and resp.json()["status"] == "CANCELLED"
    event = db.scalar(select(StatusEvent).where(StatusEvent.donation_id == donation["id"]).order_by(StatusEvent.id.desc()))
    assert (event.actor, event.reason) == ("ADMIN", "No toy recycler in the city; donor informed")


def test_admin_requeue_of_a_stalled_acceptance_goes_to_another_organisation(client, db):
    donor = h.donor(client)
    first, first_id = h.verified_acceptor(client, db, at=h.NEAR)
    _, second_id = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    donation = h.create_donation(client, donor, **h.window(length=timedelta(days=20)))
    h.offer(client, donor, donation["id"])
    h.accept(client, first, donation["id"])

    later = datetime.now(UTC) + STALL_TIMEOUTS[DonationStatus.ACCEPTED] + timedelta(minutes=1)
    report = sweeper.sweep(db, later)
    assert [(i.from_state, i.action, i.to_state) for i in report.applied] == [("ACCEPTED", "STALL", "NEEDS_ADMIN")]
    # The reneging organisation no longer sees the address.
    assert client.get(f"/organisations/me/donations/{donation['id']}", headers=first).json()["address_released"] is False

    admin = h.admin(client, db)
    resp = client.post(f"/admin/donations/{donation['id']}/requeue", headers=admin, json={"reason": "Acceptor unreachable"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "MATCHED"
    detail = client.get(f"/admin/donations/{donation['id']}", headers=admin).json()
    assert [o["organization_id"] for o in detail["timeline"]["offers"]] == [first_id, second_id]
    assert detail["timeline"]["events"][-2]["reason"] == "Acceptor unreachable"


def test_admin_list_is_redacted_and_detail_reads_are_recorded(client, db):
    donor = h.donor(client)
    donation = h.create_donation(client, donor)
    admin = h.admin(client, db)

    listed = client.get("/admin/donations", headers=admin).json()
    assert all("pickup_address_text" not in d for d in listed)

    def logged() -> int:
        return db.scalar(
            select(func.count()).select_from(AddressAccessEvent).where(AddressAccessEvent.donation_id == donation["id"])
        )

    assert logged() == 0
    detail = client.get(f"/admin/donations/{donation['id']}", headers=admin).json()
    assert detail["donation"]["pickup_address_text"]
    assert client.get(f"/donations/{donation['id']}", headers=admin).status_code == 200
    assert logged() == 2
    kinds = set(db.scalars(select(AddressAccessEvent.kind).where(AddressAccessEvent.donation_id == donation["id"])))
    assert kinds == {"ADMIN_VIEWED"}
    # The donor reading their own donation is not an audited disclosure.
    h.status(client, donor, donation["id"])
    assert logged() == 2


def test_admin_detail_shows_ranking_runs_and_reasons(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, at=h.NEAR)
    h.verified_acceptor(client, db, at=h.KORAMANGALA)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]
    client.post(
        f"/organisations/me/offers/{match_id}/reject",
        headers=org_headers,
        json={"reason_code": "NO_CAPACITY", "note": "Store room full until March"},
    )
    detail = client.get(f"/admin/donations/{donation['id']}", headers=h.admin(client, db)).json()
    assert [r["trigger"] for r in detail["ranking_runs"]] == ["DONOR_OFFER", "RE_MATCHING"]
    assert [len(r["slate"]) for r in detail["ranking_runs"]] == [2, 1]
    assert detail["timeline"]["offers"][0]["note"] == "Store room full until March"
    # The donor sees the reason code but not the acceptor's free-text note.
    donor_view = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert donor_view["offers"][0]["reason_code"] == "NO_CAPACITY"
    assert donor_view["offers"][0]["note"] is None


def test_recyclers_list(client, db):
    h.add_recycler(db, "Peenya Textiles")
    names = [r["name"] for r in client.get("/admin/recyclers", headers=h.admin(client, db)).json()]
    assert "Peenya Textiles" in names


def test_recycling_rate_is_copied_at_assignment(client, db):
    collector = h.add_recycler(db, "Peenya Textiles", rate="12.00")
    donor, donation = _escalated(client, db)
    client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    collector.rate_per_kg = 99  # a later rate change ...
    db.commit()
    assignment = db.scalar(select(Recycling).where(Recycling.donation_id == donation["id"]))
    assert str(assignment.rate_per_kg) == "12.00"  # ... does not rewrite the assignment
