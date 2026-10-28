"""Platform-arranged pickup, its SIMULATED payment, the donor wallet and the
commission ledger."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.constants import HANDOVER_GRACE
from app.services import sweeper
from tests.api import helpers as h


def _accepted(client, db, **org):
    donor = h.donor(client)
    org_headers, org_id = h.verified_acceptor(client, db, **org)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])
    return donor, org_headers, org_id, donation


def _credit_wallet(client, db, donor_headers, admin_headers, suffix: str) -> Decimal:
    """Confirms a recycling settlement for this donor and returns the credit."""
    h.add_recycler(db, f"Credit Recycler {suffix}", at=h.PEENYA, categories=("CLOTHES",), rate="100.00")
    donation = h.create_donation(
        client, donor_headers, pickup_latitude=h.NELAMANGALA[0], pickup_longitude=h.NELAMANGALA[1]
    )
    h.offer(client, donor_headers, donation["id"])  # no candidates there: ESCALATED at once
    resp = client.post(f"/donations/{donation['id']}/redirect-to-recycling", headers=donor_headers)
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/donations/{donation['id']}/deliver-to-recycler", headers=donor_headers)
    assert resp.status_code == 200, resp.text
    resp = client.post(
        f"/admin/donations/{donation['id']}/confirm-recycled", headers=admin_headers, json={"reason": "test"}
    )
    assert resp.status_code == 200, resp.text
    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor_headers).json()
    settlement = timeline["recyclings"][0]["settlement"]
    return Decimal(settlement["donor_credit"])


def test_pickup_quote_lists_only_active_providers_and_the_wallet_balance(client, db):
    donor, _, _, donation = _accepted(client, db)
    h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    h.add_provider(db, "Sleepy Co", active=False)
    resp = client.get(f"/donations/{donation['id']}/pickup-quote", headers=donor)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["wallet_balance"] == "0.00"
    assert [p["provider_name"] for p in body["providers"]] == ["Swift"]
    assert body["simulated"] is True


def test_pickup_quote_requires_a_holding_organisation(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window())  # LISTED: nobody holds it
    resp = client.get(f"/donations/{donation['id']}/pickup-quote", headers=donor)
    assert resp.status_code == 409


def test_a_donor_with_no_wallet_balance_can_still_book_and_pay_in_full(client, db):
    """The wallet is optional, not a requirement."""
    donor, org_headers, _, donation = _accepted(client, db)
    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/donations/{donation['id']}/book-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": future, "wallet_amount": "0"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "PICKUP_SCHEDULED"
    assert body["allowed_actions"] == ["MARK_HANDED_OVER"]

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert len(timeline["bookings"]) == 1
    booking = timeline["bookings"][0]
    assert booking["status"] == "BOOKED"
    assert booking["wallet_applied"] == "0.00"
    assert Decimal(booking["gateway_amount"]) == Decimal(booking["cost"])
    assert booking["payment"]["status"] == "SUCCEEDED"
    assert booking["payment"]["refunded_at"] is None


def test_book_pickup_with_partial_wallet_credit_then_full_handover_to_completed(client, db):
    donor, org_headers, _, donation = _accepted(client, db)
    admin_headers = h.admin(client, db)
    credit = _credit_wallet(client, db, donor, admin_headers, suffix="A")
    assert credit > 0

    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    quote = client.get(f"/donations/{donation['id']}/pickup-quote", headers=donor).json()
    assert Decimal(quote["wallet_balance"]) == credit
    cost = next(p["cost"] for p in quote["providers"] if p["provider_name"] == "Swift")

    requested = Decimal("1.00")  # deliberately far less than both the balance and the cost
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/donations/{donation['id']}/book-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": future, "wallet_amount": str(requested)},
    )
    assert resp.status_code == 200, resp.text

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    booking = timeline["bookings"][0]
    assert Decimal(booking["cost"]) == Decimal(cost)
    assert Decimal(booking["wallet_applied"]) == requested
    assert Decimal(booking["gateway_amount"]) == Decimal(cost) - requested
    assert Decimal(booking["wallet_applied"]) + Decimal(booking["gateway_amount"]) == Decimal(booking["cost"])

    wallet = client.get("/wallet", headers=donor).json()
    assert Decimal(wallet["balance"]) == credit - requested

    # The handover: donor hands to the courier, acceptor confirms receipt.
    body = client.post(f"/donations/{donation['id']}/mark-handed-over", headers=donor).json()
    assert body["status"] == "IN_TRANSIT"
    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert timeline["bookings"][0]["status"] == "PICKED_UP"

    resp = client.post(f"/organisations/me/donations/{donation['id']}/confirm-receipt", headers=org_headers)
    assert resp.status_code == 200 and resp.json()["status"] == "COMPLETED"
    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    assert timeline["bookings"][0]["status"] == "DELIVERED"


def test_a_stalled_booking_is_cancelled_and_refunded(client, db):
    """Nothing may be left paid but undelivered: the sweeper's STALL out of
    PICKUP_SCHEDULED cancels the booking and refunds its payment and wallet portion."""
    donor, org_headers, _, donation = _accepted(client, db)
    admin_headers = h.admin(client, db)
    credit = _credit_wallet(client, db, donor, admin_headers, suffix="B")
    # Before booking: only the recycling's commission is on the ledger. Booking adds
    # its own entry, which the refund must reverse back to exactly this.
    commission_before = Decimal(client.get("/admin/commission", headers=admin_headers).json()["total"])

    provider = h.add_provider(db, "Swift", base_fee="20.00", per_km_rate="10.00")
    scheduled_for = datetime.now(UTC) + timedelta(days=1)
    wallet_amount = Decimal("5.00")
    resp = client.post(
        f"/donations/{donation['id']}/book-pickup",
        headers=donor,
        json={
            "provider_id": str(provider.id),
            "scheduled_for": scheduled_for.isoformat(),
            "wallet_amount": str(wallet_amount),
        },
    )
    assert resp.status_code == 200, resp.text
    wallet_after_booking = Decimal(client.get("/wallet", headers=donor).json()["balance"])
    assert wallet_after_booking == credit - wallet_amount
    assert Decimal(client.get("/admin/commission", headers=admin_headers).json()["total"]) > commission_before

    # Never handed over: the sweeper stalls PICKUP_SCHEDULED after the handover grace.
    report = sweeper.sweep(db, scheduled_for + HANDOVER_GRACE)
    applied = [(i.from_state, i.action, i.to_state) for i in report.applied]
    assert ("PICKUP_SCHEDULED", "STALL", "NEEDS_ADMIN") in applied

    status = h.status(client, donor, donation["id"])
    assert status["status"] == "NEEDS_ADMIN"

    timeline = client.get(f"/donations/{donation['id']}/timeline", headers=donor).json()
    booking = timeline["bookings"][0]
    assert booking["status"] == "CANCELLED"
    assert booking["cancel_reason"]
    assert booking["payment"]["status"] == "REFUNDED"
    assert booking["payment"]["refund_transaction_id"]

    # The wallet portion came back.
    wallet_after_refund = Decimal(client.get("/wallet", headers=donor).json()["balance"])
    assert wallet_after_refund == wallet_after_booking + wallet_amount == credit

    # The commission earned on this booking was reversed: net back to where it was.
    commission_after = Decimal(client.get("/admin/commission", headers=admin_headers).json()["total"])
    assert commission_after == commission_before

    # The admin can requeue or cancel; the booking stays settled either way.
    resp = client.post(
        f"/admin/donations/{donation['id']}/cancel", headers=admin_headers, json={"reason": "abandoned"}
    )
    assert resp.status_code == 200 and resp.json()["status"] == "CANCELLED"


def test_confirming_a_recycling_credits_the_wallet_and_the_commission_ledger(client, db):
    donor = h.donor(client)
    admin_headers = h.admin(client, db)
    assert client.get("/wallet", headers=donor).json()["balance"] == "0.00"

    credit = _credit_wallet(client, db, donor, admin_headers, suffix="C")
    wallet = client.get("/wallet", headers=donor).json()
    assert Decimal(wallet["balance"]) == credit
    assert wallet["transactions"][0]["type"] == "RECYCLING_CREDIT"

    ledger = client.get("/admin/commission", headers=admin_headers).json()
    assert any(e["source"] == "RECYCLING" and Decimal(e["amount"]) > 0 for e in ledger["entries"])
