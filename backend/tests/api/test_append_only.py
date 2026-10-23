"""Non-negotiable 3, enforced in code (app.db.AppendOnly), not by database triggers:
rows are never deleted, never overwritten, and write-once columns are set once from NULL."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.constants import OfferResponse
from app.db import AppendOnlyViolation
from app.models import Match, RankingRun, StatusEvent
from tests.api import helpers as h


@pytest.fixture
def offered(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    h.offer(client, donor, donation["id"])
    db.expire_all()
    return db.scalar(select(Match).where(Match.donation_id == donation["id"]))


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
