"""Invariant: one accepted donation carries at most ONE handover path.

Once the donor has chosen a path (CHOOSE_ACCEPTOR_COLLECTION, CHOOSE_DROPOFF or
BOOK_PICKUP), the other two are refused, and the organisation's SCHEDULE_PICKUP is refused
unless the acceptor path was the one chosen. The database view of the same fact: the
acceptance has exactly one Handover row, with one mode."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Handover
from tests.api import helpers as h


def _accepted(client, db, *, pickup_capable: bool):
    h.add_provider(db)
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db, pickup_capable=pickup_capable)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    accepted = h.accept(client, org_headers, donation["id"])
    return donor, org_headers, donation["id"], accepted["match_id"]


def _when() -> str:
    return (datetime.now(UTC) + timedelta(days=1)).isoformat()


def _handover_modes(db, match_id) -> list[str]:
    db.expire_all()
    return [str(h_.mode) for h_ in db.scalars(select(Handover).where(Handover.match_id == match_id))]


def test_choosing_acceptor_collection_refuses_the_donors_other_two_paths(client, db):
    donor, _, did, match_id = _accepted(client, db, pickup_capable=True)
    h.choose_acceptor_collection(client, donor, did)

    dropoff = client.post(f"/donations/{did}/choose-dropoff", headers=donor, json={"scheduled_for": _when()})
    booking = client.post(
        f"/donations/{did}/book-pickup",
        headers=donor,
        json={"provider_id": _provider_id(client, donor, did), "scheduled_for": _when(), "wallet_amount": "0.00"},
    )
    assert dropoff.status_code == 409, dropoff.text
    assert booking.status_code == 409, booking.text
    assert _handover_modes(db, match_id) == []  # nothing scheduled by the refused calls


@pytest.mark.parametrize("first", ["DROPOFF", "BOOKING"])
def test_a_donor_path_chosen_first_refuses_the_acceptor_path_and_the_other_donor_path(client, db, first):
    donor, org_headers, did, match_id = _accepted(client, db, pickup_capable=True)
    if first == "DROPOFF":
        assert client.post(f"/donations/{did}/choose-dropoff", headers=donor, json={"scheduled_for": _when()}).status_code == 200
        other = client.post(
            f"/donations/{did}/book-pickup",
            headers=donor,
            json={"provider_id": _provider_id(client, donor, did), "scheduled_for": _when(), "wallet_amount": "0.00"},
        )
    else:
        assert client.post(
            f"/donations/{did}/book-pickup",
            headers=donor,
            json={"provider_id": _provider_id(client, donor, did), "scheduled_for": _when(), "wallet_amount": "0.00"},
        ).status_code == 200
        other = client.post(f"/donations/{did}/choose-dropoff", headers=donor, json={"scheduled_for": _when()})
    assert other.status_code == 409, other.text

    # The donation has left ACCEPTED, so neither the acceptor's choice nor its schedule applies.
    assert client.post(f"/donations/{did}/choose-acceptor-collection", headers=donor).status_code == 409
    scheduled = client.post(
        f"/organisations/me/donations/{did}/schedule-pickup", headers=org_headers, json={"scheduled_for": _when()}
    )
    assert scheduled.status_code == 409, scheduled.text

    modes = _handover_modes(db, match_id)
    assert len(modes) == 1, modes
    assert modes[0] == ("DONOR_DROPOFF" if first == "DROPOFF" else "PLATFORM_PICKUP")


def test_the_acceptor_path_chosen_then_scheduled_leaves_exactly_one_handover(client, db):
    donor, org_headers, did, match_id = _accepted(client, db, pickup_capable=True)
    h.choose_acceptor_collection(client, donor, did)
    assert client.post(
        f"/organisations/me/donations/{did}/schedule-pickup", headers=org_headers, json={"scheduled_for": _when()}
    ).status_code == 200
    assert _handover_modes(db, match_id) == ["ACCEPTOR_PICKUP"]


def _provider_id(client, donor, did) -> str:
    return client.get(f"/donations/{did}/pickup-quote", headers=donor).json()["providers"][0]["provider_id"]
