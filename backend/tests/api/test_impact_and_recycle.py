"""Two things added together: the donor's "send to recycling" entry point (creates a
donation straight into WASTE_REDIRECTED, never offered to an organisation), and impact
records written when a donation reaches an outcome (estimates, reuse and recycling apart).

Also pins the donor's view of the three handover paths against the organisation's."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.constants import CARBON_FACTOR_KG_PER_ITEM, CATEGORY_WEIGHT_KG, Category
from app.db import AppendOnlyViolation
from app.models import ImpactRecord, Match, Recycling, StatusEvent
from tests.api import helpers as h


def _recycle_payload(**overrides) -> dict:
    payload = {
        "category": "TOYS",
        "quantity": 6,
        "pickup_address_text": "45 Indiranagar 100ft Rd, Bengaluru",
        "pickup_latitude": 12.9784,
        "pickup_longitude": 77.6408,
        **h.window(),
    }
    payload.update(overrides)
    return payload


def _send_to_recycling(client, headers, **overrides):
    resp = client.post("/donations/recycle", headers=headers, json=_recycle_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Send to recycling ---------------------------------------------------------------------


def test_send_to_recycling_creates_the_donation_already_redirected_with_donor_choice(client, db):
    h.add_recycler(db, "Green Loop", categories=("TOYS",))
    donor = h.donor(client)
    body = _send_to_recycling(client, donor)

    assert body["status"] == "WASTE_REDIRECTED"
    assert body["condition"] is None
    # No logistics provider seeded in this test, so only the drop-off path is offered.
    assert body["allowed_actions"] == ["DELIVER_TO_RECYCLER"]

    donation_id = body["id"]
    event = db.scalar(select(StatusEvent).where(StatusEvent.donation_id == donation_id))
    assert (event.from_state, event.to_state, event.action, event.actor) == (
        "LISTED", "WASTE_REDIRECTED", "REDIRECT_TO_RECYCLING", "DONOR"
    )
    assert event.reason == "DONOR_CHOICE"
    assert db.scalar(select(Recycling).where(Recycling.donation_id == donation_id)) is not None
    # Never offered: no offer row exists for it.
    assert db.scalars(select(Match).where(Match.donation_id == donation_id)).all() == []


def test_send_to_recycling_with_no_recycler_goes_to_the_admin_queue(client, db):
    donor = h.donor(client)
    body = _send_to_recycling(client, donor)
    assert body["status"] == "NEEDS_ADMIN"
    reasons = [e.action for e in db.scalars(select(StatusEvent).where(StatusEvent.donation_id == body["id"]))]
    assert reasons == ["REDIRECT_TO_RECYCLING", "NO_RECYCLER"]


def test_send_to_recycling_validates_its_window_like_a_donation(client, db):
    donor = h.donor(client)
    past = h.window(start_in=timedelta(days=-3), length=timedelta(days=1))
    resp = client.post("/donations/recycle", headers=donor, json=_recycle_payload(**past))
    assert resp.status_code == 422


def test_a_listed_donation_cannot_be_sent_to_recycling_from_its_page(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window())
    assert "REDIRECT_TO_RECYCLING" not in client.get(f"/donations/{donation['id']}", headers=donor).json()["allowed_actions"]
    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor)
    assert resp.status_code == 409


# --- Handover paths: the donor chooses first; the two sides never see competing paths --------


def test_accepted_pickup_capable_the_donor_sees_three_choices_the_organisation_waits(client, db):
    h.add_provider(db)
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=True)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    accepted = h.accept(client, org_headers, donation["id"])

    detail = client.get(f"/donations/{donation['id']}", headers=donor).json()
    # The donor's three choices, as allowed_actions: nothing is chosen yet, so there is
    # nothing informational to show either.
    assert set(detail["allowed_actions"]) == {"CHOOSE_ACCEPTOR_COLLECTION", "CHOOSE_DROPOFF", "BOOK_PICKUP"}
    assert detail["handover_options"] == []
    # The organisation has no schedule action yet, and knows it is waiting on the donor.
    assert "SCHEDULE_PICKUP" not in accepted["allowed_actions"]
    assert accepted["awaiting_donor_handover_choice"] is True


def test_the_donors_choice_unlocks_the_organisation_and_hides_the_donors_own_other_paths(client, db):
    h.add_provider(db)
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=True)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])

    chosen = h.choose_acceptor_collection(client, donor, donation["id"])
    assert chosen["status"] == "ACCEPTED"  # a self-loop: no state change
    # The donor's other two paths, and choosing again, are gone.
    assert chosen["allowed_actions"] == []
    # The chosen path shown informationally while it waits to be scheduled.
    assert chosen["handover_options"] == [{"path": "ACCEPTOR_PICKUP", "available": True, "you_do_it": False}]

    acc = client.get("/organisations/me/donations/" + donation["id"], headers=org_headers).json()
    assert acc["allowed_actions"] == ["SCHEDULE_PICKUP"]
    assert acc["awaiting_donor_handover_choice"] is False

    # Choosing twice, or switching to another path after choosing, is refused.
    assert client.post(f"/donations/{donation['id']}/choose-acceptor-collection", headers=donor).status_code == 409
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert client.post(f"/donations/{donation['id']}/choose-dropoff", headers=donor, json={"scheduled_for": when}).status_code == 409


def test_drop_off_still_works_without_any_choice_first(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=True)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])

    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(f"/donations/{donation['id']}/choose-dropoff", headers=donor, json={"scheduled_for": when})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PICKUP_SCHEDULED"
    assert resp.json()["handover_options"] == []  # no longer ACCEPTED


def test_platform_pickup_still_works_without_any_choice_first(client, db):
    h.add_provider(db)
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=True)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])

    provider_id = client.get(f"/donations/{donation['id']}/pickup-quote", headers=donor).json()["providers"][0]["provider_id"]
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/donations/{donation['id']}/book-pickup",
        headers=donor,
        json={"provider_id": provider_id, "scheduled_for": when, "wallet_amount": "0.00"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PICKUP_SCHEDULED"


def test_a_non_collecting_organisation_offers_neither_side_the_collection_path(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=False)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    accepted = h.accept(client, org_headers, donation["id"])

    detail = client.get(f"/donations/{donation['id']}", headers=donor).json()
    assert "CHOOSE_ACCEPTOR_COLLECTION" not in detail["allowed_actions"]
    assert detail["handover_options"] == []
    assert "BOOK_PICKUP" not in detail["allowed_actions"]  # no provider was seeded
    # Nothing to wait on: this organisation was never going to get a schedule action.
    assert accepted["awaiting_donor_handover_choice"] is False
    assert client.post(f"/donations/{donation['id']}/choose-acceptor-collection", headers=donor).status_code == 409


# --- Impact records ------------------------------------------------------------------------


def _reused(client, db, org_headers, donor, quantity=4):
    donation = h.create_donation(client, donor, quantity=quantity, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(f"/donations/{donation['id']}/choose-dropoff", headers=donor, json={"scheduled_for": when})
    assert resp.status_code == 200, resp.text
    done = client.post(f"/organisations/me/donations/{donation['id']}/confirm-receipt", headers=org_headers)
    assert done.json()["status"] == "COMPLETED", done.text
    return donation


def test_a_completed_donation_is_recorded_as_reuse_with_estimated_mass_and_carbon(client, db):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db)
    _reused(client, db, org_headers, donor, quantity=4)

    mine = client.get("/impact/me", headers=donor).json()
    assert mine["estimated"] is True and mine["placeholders"] is True
    assert (mine["reused_donations"], mine["reused_items"]) == (1, 4)
    assert mine["reused_mass_kg"] == pytest.approx(float(CATEGORY_WEIGHT_KG[Category.CLOTHES] * 4))
    assert mine["carbon_avoided_kg"] == pytest.approx(float(CARBON_FACTOR_KG_PER_ITEM[Category.CLOTHES] * 4))
    assert (mine["recycled_donations"], mine["recycled_items"]) == (0, 0)

    theirs = client.get("/impact/organisation", headers=org_headers).json()
    assert (theirs["reused_donations"], theirs["reused_items"]) == (1, 4)
    assert theirs["carbon_avoided_kg"] == pytest.approx(mine["carbon_avoided_kg"])


def test_a_recycled_donation_counts_as_recycled_mass_and_never_as_reuse_or_carbon(client, db):
    donor = h.donor(client)
    admin = h.admin(client, db)
    h.add_recycler(db, "Loop Two", categories=("TOYS",))
    body = _send_to_recycling(client, donor, quantity=3)
    assert client.post(f"/donations/{body['id']}/deliver-to-recycler", headers=donor).status_code == 200
    resp = client.post(f"/admin/donations/{body['id']}/confirm-recycled", headers=admin, json={"reason": "test"})
    assert resp.status_code == 200, resp.text

    mine = client.get("/impact/me", headers=donor).json()
    assert (mine["recycled_donations"], mine["recycled_items"]) == (1, 3)
    assert mine["recycled_mass_kg"] == pytest.approx(float(CATEGORY_WEIGHT_KG[Category.TOYS] * 3))
    assert (mine["reused_donations"], mine["reused_items"]) == (0, 0)
    assert mine["carbon_avoided_kg"] == 0


def test_a_cancelled_donation_writes_no_impact_record(client, db):
    donor = h.donor(client)
    donation = h.create_donation(client, donor, **h.window())
    assert client.post(f"/donations/{donation['id']}/cancel", headers=donor).status_code == 200
    assert db.scalars(select(ImpactRecord).where(ImpactRecord.donation_id == donation["id"])).all() == []
    assert client.get("/impact/me", headers=donor).json()["reused_items"] == 0


def test_an_impact_record_is_append_only(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db)
    _reused(client, db, org_headers, donor)
    record = db.scalar(select(ImpactRecord))
    record.quantity = 999
    with pytest.raises(AppendOnlyViolation, match="ImpactRecord.quantity is immutable"):
        db.flush()
    db.rollback()


def test_only_an_organisation_sees_organisation_impact_and_only_a_donor_sees_donor_impact(client, db):
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db)
    assert client.get("/impact/me", headers=org_headers).status_code == 403
    assert client.get("/impact/organisation", headers=donor).status_code == 403
