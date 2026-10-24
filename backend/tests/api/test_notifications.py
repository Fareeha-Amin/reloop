"""The in-app notification feed: who sees which status events."""

from datetime import UTC, datetime, timedelta

from app.constants import STALL_TIMEOUTS, DonationStatus
from app.services import sweeper
from tests.api import helpers as h


def _feed(client, headers, **params) -> list[dict]:
    resp = client.get("/notifications", headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _actions(items: list[dict], donation_id: str) -> list[str]:
    """Oldest first, for readability."""
    return [i["action"] for i in reversed(items) if i["donation_id"] == donation_id]


def test_requires_login(client):
    assert client.get("/notifications").status_code == 401


def test_donor_sees_every_event_on_own_donations_and_nothing_else(client, db):
    donor, other_donor = h.donor(client), h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], org_id)
    h.reject(client, org_headers, donation["id"])  # no other candidate: escalates

    items = _feed(client, donor)
    assert _actions(items, donation["id"]) == ["OFFER", "REJECT", "ESCALATE"]
    assert items[0]["action"] == "ESCALATE"  # newest first
    assert items[0]["cause"] == "NO_CANDIDATES"
    offered = next(i for i in items if i["action"] == "OFFER")
    assert offered["organization_name"] == "Sunrise Children's Home"
    assert offered["category"] == "CLOTHES" and offered["quantity"] == 12
    assert _feed(client, other_donor) == []


def test_acceptor_sees_its_own_offers_only(client, db):
    donor = h.donor(client)
    a_headers, a_id = h.verified_acceptor(client, db, at=h.NEAR)
    b_headers, _ = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], a_id)
    h.reject(client, a_headers, donation["id"], "NO_CAPACITY")  # re-offered to B
    h.accept(client, b_headers, donation["id"])

    assert _actions(_feed(client, a_headers), donation["id"]) == ["OFFER", "REJECT"]
    assert _actions(_feed(client, b_headers), donation["id"]) == ["REOFFER", "ACCEPT"]


def test_holder_sees_a_stall_to_the_admin_queue_but_not_what_follows(client, db):
    donor = h.donor(client)
    a_headers, a_id = h.verified_acceptor(client, db, at=h.NEAR)
    b_headers, _ = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    admin = h.admin(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], a_id)
    h.accept(client, a_headers, donation["id"])

    later = datetime.now(UTC) + STALL_TIMEOUTS[DonationStatus.ACCEPTED] + timedelta(minutes=1)
    sweeper.sweep(db, later)
    resp = client.post(f"/admin/donations/{donation['id']}/requeue", headers=admin, json={"reason": "Reneged"})
    assert resp.status_code == 200, resp.text  # re-offered to B

    assert _actions(_feed(client, a_headers), donation["id"]) == ["OFFER", "ACCEPT", "STALL"]
    assert _actions(_feed(client, b_headers), donation["id"]) == ["REOFFER"]
    admin_items = [i for i in _feed(client, admin) if i["donation_id"] == donation["id"]]
    assert [(i["action"], i["to_state"]) for i in admin_items] == [("STALL", "NEEDS_ADMIN")]


def test_admin_sees_donations_that_need_an_admin(client, db):
    donor = h.donor(client)
    admin = h.admin(client, db)
    donation = h.create_donation(client, donor, pickup_latitude=h.NELAMANGALA[0], pickup_longitude=h.NELAMANGALA[1])
    h.offer(client, donor, donation["id"])  # no candidates: ESCALATED
    h.add_recycler(db, "GreenCycle")
    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    assert resp.status_code == 200, resp.text

    items = [i for i in _feed(client, admin) if i["donation_id"] == donation["id"]]
    assert [(i["action"], i["to_state"]) for i in items] == [("REDIRECT_TO_RECYCLING", "WASTE_REDIRECTED")]


def test_reasons_and_notes_never_appear(client, db):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], org_id)
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]
    resp = client.post(
        f"/organisations/me/offers/{match_id}/reject",
        headers=org_headers,
        json={"reason_code": "OTHER", "note": "Private remark"},
    )
    assert resp.status_code == 200, resp.text

    for headers in (donor, org_headers):
        for item in _feed(client, headers):
            assert "reason" not in item and "note" not in item
            assert "Private remark" not in str(item)


def test_paging(client, db):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], org_id)
    h.reject(client, org_headers, donation["id"])

    everything = _feed(client, donor)
    assert len(everything) == 3
    assert _feed(client, donor, limit=1) == everything[:1]
    assert _feed(client, donor, limit=2, offset=1) == everything[1:]
