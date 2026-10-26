"""Non-negotiable 3, enforced in code (app.db.AppendOnly), not by database triggers:
rows are never deleted, never overwritten, and write-once columns are set once from NULL."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.constants import OfferResponse
from app.db import AppendOnlyViolation
from app.models import Booking, Commission, Match, Payment, RankingRun, StatusEvent, WalletTxn
from tests.api import helpers as h


@pytest.fixture
def offered(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"])
    db.expire_all()
    return db.scalar(select(Match).where(Match.donation_id == donation["id"]))


@pytest.fixture
def booked(client, db):
    """A donor, an accepted offer, and a platform-pickup booking (Phase 4)."""
    donor = h.donor(client)
    org_headers, _ = h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor, **h.window())
    h.offer(client, donor, donation["id"])
    h.accept(client, org_headers, donation["id"])
    provider = h.add_provider(db)
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    resp = client.post(
        f"/donations/{donation['id']}/book-pickup",
        headers=donor,
        json={"provider_id": str(provider.id), "scheduled_for": future, "wallet_amount": "0"},
    )
    assert resp.status_code == 200, resp.text
    db.expire_all()
    return db.scalar(select(Booking).where(Booking.donation_id == donation["id"]))


def test_match_columns_are_immutable(db, offered):
    offered.rank = 5
    with pytest.raises(AppendOnlyViolation, match="Match.rank is immutable"):
        db.flush()
    db.rollback()


def test_a_response_is_written_once_and_never_overwritten(db, offered):
    offered.respond(OfferResponse.REJECTED, datetime.now(UTC))
    db.commit()
    db.expire_all()
    match = db.get(Match, offered.id)
    with pytest.raises(ValueError):
        match.respond(OfferResponse.ACCEPTED, datetime.now(UTC))
    match.response = OfferResponse.ACCEPTED  # bypassing respond(): the guard still holds
    with pytest.raises(AppendOnlyViolation, match="write-once"):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("model", [Match, StatusEvent, RankingRun])
def test_rows_are_never_deleted(db, offered, model):
    row = db.scalar(select(model).limit(1))
    db.delete(row)
    with pytest.raises(AppendOnlyViolation, match="never deleted"):
        db.flush()
    db.rollback()


def test_status_events_are_immutable(db, offered):
    event = db.scalar(select(StatusEvent).where(StatusEvent.donation_id == offered.donation_id))
    event.reason = "rewritten history"
    with pytest.raises(AppendOnlyViolation):
        db.flush()
    db.rollback()


# --- Phase 4: bookings, payments, the commission and wallet ledgers -----------------------


def test_booking_columns_are_immutable(db, booked):
    booked.cost = booked.cost + 1
    with pytest.raises(AppendOnlyViolation, match="Booking.cost is immutable"):
        db.flush()
    db.rollback()


def test_a_booking_timestamp_is_written_once_and_never_overwritten(db, booked):
    booked.cancelled_at = datetime.now(UTC)
    booked.cancel_reason = "test"
    db.commit()
    db.expire_all()
    row = db.get(Booking, booked.id)
    row.cancelled_at = datetime.now(UTC) + timedelta(seconds=1)  # guaranteed distinct from the above
    with pytest.raises(AppendOnlyViolation, match="write-once"):
        db.flush()
    db.rollback()


def test_payment_columns_are_immutable(db, booked):
    payment = booked.payment
    payment.amount = payment.amount + 1
    with pytest.raises(AppendOnlyViolation, match="Payment.amount is immutable"):
        db.flush()
    db.rollback()


def test_a_payment_refund_is_written_once_and_never_overwritten(db, booked):
    payment = booked.payment
    payment.refunded_at = datetime.now(UTC)
    payment.refund_transaction_id = "SIM-RFD-TEST"
    db.commit()
    db.expire_all()
    row = db.get(Payment, payment.id)
    row.refunded_at = datetime.now(UTC) + timedelta(seconds=1)  # guaranteed distinct from the above
    with pytest.raises(AppendOnlyViolation, match="write-once"):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("model", [Booking, Payment])
def test_phase4_booking_rows_are_never_deleted(db, booked, model):
    row = db.scalar(select(model).limit(1))
    db.delete(row)
    with pytest.raises(AppendOnlyViolation, match="never deleted"):
        db.flush()
    db.rollback()


@pytest.fixture
def ledger_rows(db, booked):
    """A Commission row (every booking gets one) and a WalletTxn row (needs a non-zero
    wallet credit, which the booked fixture's zero-wallet booking does not produce)."""
    from decimal import Decimal

    from app.constants import WalletTxnType
    from app.services import wallet

    commission_row = db.scalar(select(Commission).limit(1))
    assert commission_row is not None
    wallet.record(
        db, booked.arranged_by_id, WalletTxnType.PICKUP_REFUND, Decimal("10.00"), datetime.now(UTC),
        reference_booking_id=booked.id,
    )
    db.commit()
    return commission_row, db.scalar(select(WalletTxn).limit(1))


def test_commission_and_wallet_rows_are_fully_immutable(db, ledger_rows):
    commission_row, txn = ledger_rows
    commission_row.amount = commission_row.amount + 1
    with pytest.raises(AppendOnlyViolation, match="immutable"):
        db.flush()
    db.rollback()

    txn.amount = txn.amount + 1
    with pytest.raises(AppendOnlyViolation, match="immutable"):
        db.flush()
    db.rollback()


@pytest.mark.parametrize("model", [Commission, WalletTxn])
def test_commission_and_wallet_rows_are_never_deleted(db, ledger_rows, model):
    row = db.scalar(select(model).limit(1))
    db.delete(row)
    with pytest.raises(AppendOnlyViolation, match="never deleted"):
        db.flush()
    db.rollback()
