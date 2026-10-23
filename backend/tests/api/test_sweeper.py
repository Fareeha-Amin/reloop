"""The deadline sweeper against the database. Time is injected: sweep(db, now)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.constants import (
    ESCALATION_TTL,
    HANDOVER_GRACE,
    LISTED_STALL,
    OFFER_TTL,
    STALL_TIMEOUTS,
    DonationStatus,
)
from app.models import Donation, Match
from app.services import sweeper
from tests.api import helpers as h


def _applied(report):
    return [(i.from_state, i.action, i.to_state) for i in report.applied]


def _row(db, donation):
    db.expire_all()
    return db.get(Donation, donation["id"])


def test_expired_offer_is_reoffered_and_a_second_sweep_does_nothing(client, db):
    donor = h.donor(client)
    first, _ = h.verified_acceptor(client, db, at=h.NEAR)
    second, _ = h.verified_acceptor(client, db, at=h.KORAMANGALA)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])

    later = datetime.now(UTC) + OFFER_TTL + timedelta(minutes=1)
    report = sweeper.sweep(db, later)
    assert _applied(report) == [("MATCHED", "EXPIRE", "MATCHED")]
    expired = db.scalar(select(Match).where(Match.donation_id == donation["id"], Match.response == "EXPIRED"))
    assert expired is not None and expired.responder_id is None
    reoffer = db.scalar(select(Match).where(Match.donation_id == donation["id"], Match.response.is_(None)))
    assert reoffer.offered_by == "SYSTEM" and reoffer.expires_at == later + OFFER_TTL

    assert _applied(sweeper.sweep(db, later)) == []  # idempotent
    assert h.inbox(client, first) == [] and len(h.inbox(client, second)) == 1


def test_a_late_answer_to_an_expired_offer_is_refused_and_closes_it(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    match_id = h.the_offer(client, org_headers, donation["id"])["match_id"]

    match = db.get(Match, match_id)
    # Simulate the passage of time: rebuild the offer as already past its TTL.
    db.execute(  # test-only: back-date the offer (app code never issues bulk updates)
        Match.__table__.update()
        .where(Match.__table__.c.id == match.id)
        .values(offered_at=datetime.now(UTC) - OFFER_TTL - timedelta(hours=1), expires_at=datetime.now(UTC) - timedelta(hours=1))
    )
    db.commit()

    resp = client.post(f"/organisations/me/offers/{match_id}/accept", headers=org_headers)
    assert resp.status_code == 409
    db.expire_all()
    assert db.get(Match, match_id).response == "EXPIRED"
    # Only organisation, now excluded: escalated with no candidates.
    assert _row(db, donation).status == DonationStatus.ESCALATED


def test_listed_donation_never_offered_escalates_after_listed_stall(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    created = db.get(Donation, donation["id"]).created_at
    assert _applied(sweeper.sweep(db, created + LISTED_STALL - timedelta(seconds=1))) == []
    assert _applied(sweeper.sweep(db, created + LISTED_STALL)) == [("LISTED", "ESCALATE", "ESCALATED")]
    body = h.status(client, donor, donation["id"])
    assert body["escalation_cause"] == "NOT_OFFERED"
    # Candidates remain, so the donor can still re-match.
    assert "REMATCH" in body["allowed_actions"]


def test_an_ended_window_never_triggers_the_sweeper(client, db):
    """The pickup window is advisory: only the offer's own TTL closes it."""
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window(length=timedelta(hours=3)))  # ends before OFFER_TTL
    h.offer(client, donor, donation["id"])
    end = datetime.fromisoformat(donation["pickup_window_end"])
    assert _applied(sweeper.sweep(db, end + timedelta(minutes=1))) == []
    match = db.scalar(select(Match).where(Match.donation_id == donation["id"]))
    assert match.response is None


def test_silent_donor_goes_to_the_admin_queue_not_to_an_end(client, db):
    donor = h.donor(client)
    donation = h.create_donation(client, donor, pickup_latitude=h.NELAMANGALA[0], pickup_longitude=h.NELAMANGALA[1])
    h.offer(client, donor, donation["id"])  # no candidates: ESCALATED now
    now = datetime.now(UTC)
    assert _applied(sweeper.sweep(db, now + ESCALATION_TTL - timedelta(minutes=1))) == []
    assert _applied(sweeper.sweep(db, now + ESCALATION_TTL + timedelta(minutes=1))) == [
        ("ESCALATED", "STALL", "NEEDS_ADMIN")
    ]
    # And it stays there: the admin queue is never swept.
    assert _applied(sweeper.sweep(db, now + timedelta(days=365))) == []


def test_pickup_scheduled_stalls_after_the_handover_time_and_in_transit_after_its_timeout(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])
    at = datetime.fromisoformat(donation["pickup_window_start"]) + timedelta(hours=1)
    client.post(
        f"/organisations/me/donations/{donation['id']}/schedule-pickup",
        headers=org_headers,
        json={"scheduled_for": at.isoformat()},
    )
    # Measured from the agreed handover time, not from entering the state.
    assert _applied(sweeper.sweep(db, at + HANDOVER_GRACE - timedelta(minutes=1))) == []

    client.post(f"/donations/{donation['id']}/mark-handed-over", headers=donor)
    soon = datetime.now(UTC) + STALL_TIMEOUTS[DonationStatus.IN_TRANSIT] + timedelta(minutes=1)
    assert _applied(sweeper.sweep(db, soon)) == [("IN_TRANSIT", "STALL", "NEEDS_ADMIN")]


def test_sweep_endpoint(client, db):
    resp = client.post("/admin/sweep", headers=h.admin(client, db))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {"now", "examined", "skipped_locked", "applied", "errors"} <= set(body)
    assert body["errors"] == []


def test_cli_sweep_runs_against_the_configured_database(test_engine, monkeypatch, capsys):
    import app.cli as cli

    monkeypatch.setattr(cli, "get_engine", lambda: test_engine)
    assert cli.main(["sweep"]) == 0
    assert "Swept at" in capsys.readouterr().out
