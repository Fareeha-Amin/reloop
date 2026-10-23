"""The manual acceptance test (README, "Acceptance test (Phase 2)"), automated.

Offer order is not a fixed fact: it depends on every verified organisation in the
database and on each one's accept/reject history. So, like the README steps, this
script never names who should be offered next. It follows whoever holds the open offer
(timeline: the offer with no response) and finds that organisation's login through
GET /admin/organisations/{id}. It runs on the seed data alone, and again with one extra
verified organisation that is not in the seed (as on a database that kept Phase 1's
/docs example, "Sunrise Home"), which changes the order of the offers.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services import seed
from tests.api import helpers as h

NELAMANGALA = {
    "pickup_latitude": 13.0977,
    "pickup_longitude": 77.3910,
    "pickup_address_text": "Nelamangala Town, Bengaluru Rural",
}
MG_ROAD = (12.9716, 77.5946)  # where Phase 1's /docs example organisation sits


def _open_offer(client, donor, donation_id) -> dict:
    offers = client.get(f"/donations/{donation_id}/timeline", headers=donor).json()["offers"]
    open_offers = [o for o in offers if o["response"] is None]
    assert len(open_offers) == 1
    return open_offers[0]


def _holder_login(client, donor, admin, donation_id) -> dict:
    """Log in as whichever organisation holds the open offer. Every account in this
    test database shares h.PASSWORD."""
    org_id = _open_offer(client, donor, donation_id)["organization_id"]
    email = client.get(f"/admin/organisations/{org_id}", headers=admin).json()["account_email"]
    return h.auth(h.login(client, email))


@pytest.mark.parametrize("extra_org", [False, True], ids=["seed-only", "seed-plus-non-seed-org"])
def test_acceptance_script(client, db, extra_org):
    seed.seed(db, h.PASSWORD)
    if extra_org:
        headers, _ = h.verified_acceptor(client, db, at=MG_ROAD)
        h.add_need(client, headers, category="CLOTHES", urgency="HIGH")
    donor = h.auth(h.login(client, seed.DEMO_DONOR_EMAIL))
    admin = h.admin(client, db)

    # A. Rejected until it escalates, then COMPLETED.
    a = h.create_donation(client, donor, **h.window())
    assert client.get(f"/donations/{a['id']}/candidates", headers=donor).json()["candidates"]
    assert h.offer(client, donor, a["id"])["status"] == "MATCHED"
    holders = []
    for _ in range(3):
        holders.append(_open_offer(client, donor, a["id"])["organization_id"])
        h.reject(client, _holder_login(client, donor, admin, a["id"]), a["id"])
    body = h.status(client, donor, a["id"])
    assert (body["status"], body["escalation_cause"]) == ("ESCALATED", "THRESHOLD_REACHED")
    assert body["allowed_actions"] == ["CANCEL", "REDIRECT_TO_RECYCLING", "REMATCH", "UPGRADE_PRIORITY"]

    assert client.post(f"/donations/{a['id']}/rematch", headers=donor).json()["status"] == "MATCHED"
    holders.append(_open_offer(client, donor, a["id"])["organization_id"])
    assert len(set(holders)) == 4  # never the same organisation twice
    acceptor = _holder_login(client, donor, admin, a["id"])
    accepted = h.accept(client, acceptor, a["id"])
    assert accepted["address_released"] is True

    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    if "SCHEDULE_PICKUP" in accepted["allowed_actions"]:  # the organisation collects
        path = f"/organisations/me/donations/{a['id']}/schedule-pickup"
        resp = client.post(path, headers=acceptor, json={"scheduled_for": when})
    else:  # it does not: the donor drops off
        resp = client.post(f"/donations/{a['id']}/choose-dropoff", headers=donor, json={"scheduled_for": when})
    assert resp.json()["status"] == "PICKUP_SCHEDULED"
    assert client.post(f"/donations/{a['id']}/mark-handed-over", headers=donor).json()["status"] == "IN_TRANSIT"
    done = client.post(f"/organisations/me/donations/{a['id']}/confirm-receipt", headers=acceptor).json()
    assert (done["status"], done["address_released"]) == ("COMPLETED", False)

    # Whatever the order, each offer went to the top of the slate it was made from.
    detail = client.get(f"/admin/donations/{a['id']}", headers=admin).json()
    assert [o["rank"] for o in detail["timeline"]["offers"]] == [1, 1, 1, 1]
    assert len(detail["ranking_runs"]) == 4

    # B. No candidates -> recycling -> RECYCLED.
    b = h.create_donation(client, donor, **NELAMANGALA)
    body = h.offer(client, donor, b["id"])
    assert (body["status"], body["escalation_cause"]) == ("ESCALATED", "NO_CANDIDATES")
    assert body["allowed_actions"] == ["CANCEL", "REDIRECT_TO_RECYCLING"]
    assert client.post(f"/donations/{b['id']}/redirect-to-recycling", headers=donor).json()["status"] == "WASTE_REDIRECTED"
    assert client.post(f"/admin/donations/{b['id']}/confirm-recycled", headers=admin, json={}).status_code == 422
    resp = client.post(f"/admin/donations/{b['id']}/confirm-recycled", headers=admin, json={"reason": "Recycler confirmed"})
    assert resp.json()["status"] == "RECYCLED"
    rec = client.get(f"/donations/{b['id']}/timeline", headers=donor).json()["recyclings"][0]
    # With the seed recyclers, the only active CLOTHES recycler within range.
    assert rec["collector_name"] == "GreenCycle Textile Recovery"
    assert (rec["simulated"], rec["mass_is_estimate"], rec["weights_are_placeholders"]) == (True, True, True)

    # C. Toys -> no recycler -> NEEDS_ADMIN.
    c = h.create_donation(client, donor, category="TOYS", **NELAMANGALA)
    assert h.offer(client, donor, c["id"])["status"] == "ESCALATED"
    assert client.post(f"/donations/{c['id']}/redirect-to-recycling", headers=donor).json()["status"] == "NEEDS_ADMIN"
    item = next(i for i in client.get("/admin/queue", headers=admin).json() if i["donation"]["id"] == c["id"])
    assert (item["via"], item["allowed_actions"]) == ("NO_RECYCLER", ["CANCEL"])
    base = f"/admin/donations/{c['id']}"
    assert client.post(f"{base}/requeue", headers=admin, json={"reason": "try again"}).status_code == 409
    assert client.post(f"{base}/redirect-to-recycling", headers=admin, json={"reason": "x"}).status_code == 409
    resp = client.post(f"{base}/cancel", headers=admin, json={"reason": "No toy recycler; donor informed"})
    assert resp.json()["status"] == "CANCELLED"
