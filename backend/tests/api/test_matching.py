"""Matching, offers, rejection handling and escalation, through the API."""

from sqlalchemy import func, select

from app.constants import Actor, DonationStatus
from app.models import Donation, Match, RankingRun, StatusEvent
from tests.api import helpers as h


def _count(db, model, **where) -> int:
    query = select(func.count()).select_from(model)
    for column, value in where.items():
        query = query.where(getattr(model, column) == value)
    return db.scalar(query)


def test_candidates_preview_explains_scores_and_stores_nothing(client, db):
    donor = h.donor(client)
    needy_headers, needy = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    h.add_need(client, needy_headers, urgency="HIGH")
    _, near = h.verified_acceptor(client, db, at=h.NEAR)
    h.acceptor(client, latitude=h.NEAR[0], longitude=h.NEAR[1])  # unverified: filtered
    donation = h.create_donation(client, donor)

    resp = client.get(f"/donations/{donation['id']}/candidates", headers=donor)
    assert resp.status_code == 200, resp.text
    slate = resp.json()
    assert [c["organization_id"] for c in slate["candidates"]] == [needy, near]
    assert slate["radius_km"] == 15.0 and slate["declines"] == 0
    assert slate["filtered_out"] == {"NOT_VERIFIED": 1}
    top = slate["candidates"][0]
    assert {c["factor"] for c in top["components"]} == {
        "PROXIMITY", "NEED_MATCH", "URGENCY", "CAPACITY_HEADROOM", "ACCEPTANCE_RATE"
    }
    assert abs(sum(c["contribution"] for c in top["components"]) - top["score"]) < 1e-5
    assert _count(db, RankingRun, donation_id=donation["id"]) == 0


def test_offer_goes_to_the_top_candidate_and_stores_the_full_slate(client, db):
    donor = h.donor(client)
    top_headers, top = h.verified_acceptor(client, db, at=h.NEAR)
    h.add_need(client, top_headers)
    h.verified_acceptor(client, db, at=h.KORAMANGALA)
    h.verified_acceptor(client, db, at=h.HSR)
    donation = h.create_donation(client, donor)

    body = h.offer(client, donor, donation["id"])
    assert body["status"] == "MATCHED"
    assert body["allowed_actions"] == ["CANCEL"]

    match = db.scalar(select(Match).where(Match.donation_id == donation["id"]))
    assert (str(match.organization_id), match.rank, match.offered_by) == (top, 1, "DONOR")
    run = db.get(RankingRun, match.ranking_run_id)
    assert run.trigger == "DONOR_OFFER" and len(run.slate) == 3
    assert run.config_version and run.config["weights"]["PROXIMITY"] == 0.3
    event = db.scalar(select(StatusEvent).where(StatusEvent.donation_id == donation["id"]))
    assert (event.from_state, event.action, event.to_state, event.actor) == ("LISTED", "OFFER", "MATCHED", Actor.DONOR)
    assert event.match_id == match.id


def test_donor_may_choose_any_eligible_candidate(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db, at=h.NEAR)
    _, second = h.verified_acceptor(client, db, at=h.MALLESHWARAM)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"], organization_id=second)
    match = db.scalar(select(Match).where(Match.donation_id == donation["id"]))
    assert (str(match.organization_id), match.rank) == (second, 2)


def test_offer_to_an_ineligible_organisation_is_refused_and_stores_nothing(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db, at=h.NEAR)
    _, unverified = h.acceptor(client)
    donation = h.create_donation(client, donor)
    resp = client.post(
        f"/donations/{donation['id']}/offer",
        headers=donor,
        json={"organization_id": unverified["organization"]["id"]},
    )
    assert resp.status_code == 409
    assert _count(db, RankingRun, donation_id=donation["id"]) == 0
    assert h.status(client, donor, donation["id"])["status"] == "LISTED"


def test_offer_with_no_candidates_escalates_with_only_recycle_and_cancel(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db, at=h.NELAMANGALA)  # ~30 km away
    donation = h.create_donation(client, donor)
    body = h.offer(client, donor, donation["id"])
    assert body["status"] == "ESCALATED"
    assert body["escalation_cause"] == "NO_CANDIDATES"
    assert body["allowed_actions"] == ["CANCEL", "REDIRECT_TO_RECYCLING"]
    run = db.scalar(select(RankingRun).where(RankingRun.donation_id == donation["id"]))
    assert run.slate == [] and run.filtered_out == {"OUT_OF_RADIUS": 1}
    # No loop: re-matching an empty slate is refused.
    assert client.post(f"/donations/{donation['id']}/rematch", headers=donor).status_code == 409


def test_the_pickup_window_is_advisory_an_ended_window_does_not_block_an_offer(client, db):
    from datetime import UTC, datetime, timedelta

    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    row = db.get(Donation, donation["id"])
    row.pickup_window_start = datetime.now(UTC) - timedelta(days=2)
    row.pickup_window_end = datetime.now(UTC) - timedelta(days=1)
    db.commit()
    assert h.offer(client, donor, donation["id"])["status"] == "MATCHED"


def test_three_rejections_escalate_to_the_donor(client, db):
    donor = h.donor(client)
    orgs = [h.verified_acceptor(client, db, at=at) for at in (h.NEAR, h.KORAMANGALA, h.HSR, h.MALLESHWARAM)]
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])

    offered = []
    for _ in range(3):
        current = next(hd for hd, _ in orgs if any(o["donation_id"] == donation["id"] for o in h.inbox(client, hd)))
        offered.append(current)
        rejected = h.reject(client, current, donation["id"])
        assert rejected["response"] == "REJECTED" and rejected["allowed_actions"] == []

    assert len({id(x) for x in offered}) == 3  # never offered to the same organisation twice
    body = h.status(client, donor, donation["id"])
    assert body["status"] == "ESCALATED"
    assert body["escalation_cause"] == "THRESHOLD_REACHED"
    assert body["allowed_actions"] == ["CANCEL", "REDIRECT_TO_RECYCLING", "REMATCH", "UPGRADE_PRIORITY"]

    actions = [
        e.action
        for e in db.scalars(select(StatusEvent).where(StatusEvent.donation_id == donation["id"]).order_by(StatusEvent.id))
    ]
    assert actions == ["OFFER", "REJECT", "REOFFER", "REJECT", "REOFFER", "REJECT", "ESCALATE"]
    re_offers = db.scalars(select(Match).where(Match.donation_id == donation["id"], Match.offered_by == "SYSTEM"))
    assert len(list(re_offers)) == 2
    # RE_MATCHING is transient: never the committed status.
    assert _count(db, Donation, status=DonationStatus.RE_MATCHING) == 0


def test_rematch_after_escalation_restarts_the_count(client, db):
    donor = h.donor(client)
    orgs = [h.verified_acceptor(client, db, at=at)[0] for at in (h.NEAR, h.KORAMANGALA, h.HSR, h.MALLESHWARAM, h.INDIRANAGAR)]
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])

    def holder():
        return next(hd for hd in orgs if any(o["donation_id"] == donation["id"] for o in h.inbox(client, hd)))

    for _ in range(3):
        h.reject(client, holder(), donation["id"])
    assert h.status(client, donor, donation["id"])["status"] == "ESCALATED"

    resp = client.post(f"/donations/{donation['id']}/rematch", headers=donor)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "MATCHED"
    # One decline since the escalation is below the threshold: re-offered, not escalated.
    h.reject(client, holder(), donation["id"])
    assert h.status(client, donor, donation["id"])["status"] == "MATCHED"


def test_a_decline_widens_the_radius(client, db):
    donor = h.donor(client)
    near_headers, _ = h.verified_acceptor(client, db, at=h.NEAR)
    _, far = h.verified_acceptor(client, db, at=h.YELAHANKA)
    donation = h.create_donation(client, donor, **h.window())
    slate = client.get(f"/donations/{donation['id']}/candidates", headers=donor).json()
    assert far not in {c["organization_id"] for c in slate["candidates"]}
    assert slate["filtered_out"] == {"OUT_OF_RADIUS": 1}

    h.offer(client, donor, donation["id"])
    h.reject(client, near_headers, donation["id"])
    match = db.scalar(select(Match).where(Match.donation_id == donation["id"], Match.response.is_(None)))
    assert str(match.organization_id) == far
    assert db.get(RankingRun, match.ranking_run_id).radius_km == 18.75


def test_upgrade_priority_flags_the_donation_and_reoffers(client, db):
    donor = h.donor(client)
    orgs = [h.verified_acceptor(client, db, at=at)[0] for at in (h.NEAR, h.KORAMANGALA, h.HSR, h.MALLESHWARAM)]
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    for _ in range(3):
        current = next(hd for hd in orgs if any(o["donation_id"] == donation["id"] for o in h.inbox(client, hd)))
        h.reject(client, current, donation["id"])

    resp = client.post(f"/donations/{donation['id']}/upgrade-priority", headers=donor)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "MATCHED" and body["is_priority"] is True


def test_inbox_is_ordered_by_queue_priority(client, db):
    org_headers, _ = h.verified_acceptor(client, db, at=h.NEAR)
    plain_donor, priority_donor = h.donor(client), h.donor(client)
    plain = h.create_donation(client, plain_donor)
    priority = h.create_donation(client, priority_donor, is_priority=True)
    h.offer(client, plain_donor, plain["id"])
    h.offer(client, priority_donor, priority["id"])

    offers = h.inbox(client, org_headers)
    assert [o["donation_id"] for o in offers] == [priority["id"], plain["id"]]
    assert "queue_priority" not in offers[0]


def test_declined_donations_rise_in_the_inbox(client, db):
    """The rejection boost: a donation declined elsewhere outranks a fresh one."""
    target, _ = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    decliner, _ = h.verified_acceptor(client, db, at=h.NEAR, categories_accepted=["BOOKS"])
    fresh_donor, declined_donor = h.donor(client), h.donor(client)
    fresh = h.create_donation(client, fresh_donor)
    h.offer(client, fresh_donor, fresh["id"])
    declined = h.create_donation(client, declined_donor, category="BOOKS")
    h.offer(client, declined_donor, declined["id"])  # goes to the nearer BOOKS org first
    h.reject(client, decliner, declined["id"])  # re-offered to target with one decline

    assert [o["donation_id"] for o in h.inbox(client, target)] == [declined["id"], fresh["id"]]
