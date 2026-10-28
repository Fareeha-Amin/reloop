"""Ranking-weight training against the database: the prior, the floor, the sandbox, purge,
activation as an insert, and the labels on each breakdown."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.constants import SCORE_WEIGHTS, OfferResponse, OfferSource, RankingTrigger, ScoreFactor
from app.db import AppendOnlyViolation
from app.domain import learning
from app.domain.scoring import MatchingConfig
from app.models import Match, ModelVersion, RankingRun, SyntheticOutcome
from app.services import training
from sim import engine, world
from tests.api import helpers as h

FACTOR_VALUES = (0.9, 0.4, 0.2, 0.7, 0.5)  # PROXIMITY, NEED_MATCH, URGENCY, CAPACITY, ACCEPTANCE


def _slate_entry(org_id: uuid.UUID, rank: int, values) -> dict:
    return {
        "rank": rank,
        "organization_id": str(org_id),
        "organization_name": "Test organisation",
        "pickup_capable": True,
        "distance_km": 1.0,
        "score": 0.5,
        "components": [
            {"factor": f.value, "raw": None, "value": v, "weight": SCORE_WEIGHTS[f], "contribution": SCORE_WEIGHTS[f] * v}
            for f, v in zip(learning.FACTORS, values)
        ],
    }


def _labelled_offer(
    db, donation_id, org_id, values, response: OfferResponse, rank: int = 1, slate_org_id=None
) -> Match:
    """A real offer and its response, written directly: the rows the API would write.
    `slate_org_id` (tests only) writes a slate that shows a different organisation."""
    now = datetime.now(UTC)
    run = RankingRun(
        id=uuid.uuid4(),
        donation_id=donation_id,
        trigger=RankingTrigger.DONOR_OFFER,
        radius_km=15.0,
        declines=0,
        config_version=MatchingConfig().version(),
        config=MatchingConfig().as_dict(),
        slate=[_slate_entry(slate_org_id or org_id, rank, values)],
        filtered_out={},
        created_at=now,
    )
    match = Match(
        id=uuid.uuid4(),
        donation_id=donation_id,
        organization_id=org_id,
        ranking_run_id=run.id,
        rank=rank,
        offered_by=OfferSource.DONOR,
        offered_at=now,
        expires_at=now + timedelta(hours=48),
        response=response,
        responded_at=now,
    )
    db.add_all([run, match])
    db.flush()
    return match


def _version(db, weights: dict, *, activated: bool, real_n: int = 120, real_accepted: int = 40) -> ModelVersion:
    row = ModelVersion(
        config_version=MatchingConfig(weights=weights).version(),
        weights={f.value: w for f, w in weights.items()},
        intercept=-1.0,
        activated=activated,
        sandbox=False,
        reasons=[] if activated else ["test"],
        real_n=real_n,
        real_accepted=real_accepted,
        synthetic_n=0,
        synthetic_accepted=0,
        fit={"max_shift_from_prior": 0.1},
    )
    db.add(row)
    db.commit()
    return row


def _normalised(*values: float) -> dict:
    total = sum(values)
    return {f: v / total for f, v in zip(learning.FACTORS, values)}


def _active_weights(db) -> dict:
    return {f: float(w) for f, w in training.active_config(db).weights.items()}


def _prior_weights() -> dict:
    return {f: float(w) for f, w in MatchingConfig().weights.items()}


# --- The prior, through the API ---------------------------------------------------------------


def test_with_no_activated_fit_the_breakdown_is_the_prior(client, db):
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    body = client.get(f"/donations/{donation['id']}/candidates", headers=donor).json()
    assert body["candidates"], "the test organisation should be eligible"
    assert body["model"]["is_prior"] is True
    assert body["model"]["config_version"] == MatchingConfig().version() == body["config_version"]
    assert body["model"]["training_sample"] == {"real": 0, "real_accepted": 0, "synthetic": 0, "synthetic_accepted": 0}
    assert body["model"]["trained_at"] is None
    for component in body["candidates"][0]["components"]:
        assert component["weight"] == pytest.approx(SCORE_WEIGHTS[ScoreFactor(component["factor"])])


def test_a_retrained_breakdown_reports_its_fit_its_sample_and_still_sums_to_the_score(client, db):
    weights = _normalised(5.0, 2.0, 1.0, 1.0, 1.0)
    _version(db, weights, activated=True, real_n=120, real_accepted=40)
    donor = h.donor(client)
    h.verified_acceptor(client, db)
    donation = h.create_donation(client, donor)
    body = client.get(f"/donations/{donation['id']}/candidates", headers=donor).json()

    assert body["model"]["is_prior"] is False
    assert body["model"]["config_version"] == MatchingConfig(weights=weights).version()
    assert body["model"]["training_sample"]["real"] == 120
    assert body["model"]["training_sample"]["real_accepted"] == 40
    assert body["model"]["training_sample"]["synthetic"] == 0
    assert body["model"]["max_shift_from_prior"] == pytest.approx(0.1)
    candidate = body["candidates"][0]
    assert {c["factor"]: c["weight"] for c in candidate["components"]} == pytest.approx(
        {f.value: w for f, w in weights.items()}
    )
    assert sum(c["contribution"] for c in candidate["components"]) == pytest.approx(candidate["score"], abs=1e-5)


# --- The floor, the sandbox, purge ------------------------------------------------------------


def test_a_below_floor_run_leaves_exactly_one_unactivated_audit_row(client, db):
    """Every attempt is recorded. Below the floor: no fit, nothing activated, one row that
    carries the reason and the counts it was judged on."""
    org_id = uuid.UUID(h.verified_acceptor(client, db)[1])
    donor = h.donor(client)
    for response in (OfferResponse.ACCEPTED, OfferResponse.REJECTED, OfferResponse.EXPIRED):
        donation_id = uuid.UUID(h.create_donation(client, donor)["id"])
        _labelled_offer(db, donation_id, org_id, FACTOR_VALUES, response)
    db.commit()
    rows_before = db.scalar(select(func.count()).select_from(ModelVersion))

    report = training.train(db)

    assert db.scalar(select(func.count()).select_from(ModelVersion)) == rows_before + 1
    row = report.version
    assert row.activated is False and report.activated is False
    assert report.fitted is False
    assert row.weights is None and row.intercept is None and row.config_version is None and row.fit is None
    assert (row.real_n, row.real_accepted) == (3, 1)
    assert any("floor" in reason for reason in row.reasons)
    assert list(row.reasons) == list(report.reasons)
    assert _active_weights(db) == _prior_weights()


def test_every_attempt_writes_its_own_row_and_none_of_them_activates(db):
    before = db.scalar(select(func.count()).select_from(ModelVersion))
    training.train(db)
    training.train(db)
    assert db.scalar(select(func.count()).select_from(ModelVersion)) == before + 2
    assert db.scalar(select(func.count()).select_from(ModelVersion).where(ModelVersion.activated.is_(True))) == 0
    assert _active_weights(db) == _prior_weights()


def test_real_offers_are_read_back_with_the_features_they_were_made_against(client, db):
    orgs = [h.verified_acceptor(client, db)[1] for _ in range(2)]
    donor = h.donor(client)
    written = []
    for i in range(6):
        donation = h.create_donation(client, donor)
        values = tuple(round(0.1 * (i + j + 1), 3) for j in range(5))
        response = OfferResponse.ACCEPTED if i % 2 else OfferResponse.REJECTED
        _labelled_offer(db, uuid.UUID(donation["id"]), uuid.UUID(orgs[i % 2]), values, response)
        written.append((values, response is OfferResponse.ACCEPTED))
    db.commit()

    read = training.real_outcomes(db)
    assert sorted((o.features, o.accepted) for o in read) == sorted(written)
    report = training.train(db)
    assert report.real.total == 6 and report.real.accepted == 3 and report.real.declined == 3


def test_retracted_and_open_offers_are_not_labelled(client, db):
    org_id = uuid.UUID(h.verified_acceptor(client, db)[1])
    donor = h.donor(client)
    donation_id = uuid.UUID(h.create_donation(client, donor)["id"])
    _labelled_offer(db, donation_id, org_id, FACTOR_VALUES, OfferResponse.RETRACTED)
    db.commit()
    assert training.real_outcomes(db) == []


def test_an_offer_pointing_at_a_candidate_its_run_does_not_show_is_refused(client, db):
    org_id = uuid.UUID(h.verified_acceptor(client, db)[1])
    other = uuid.UUID(h.verified_acceptor(client, db)[1])
    donor = h.donor(client)
    donation_id = uuid.UUID(h.create_donation(client, donor)["id"])
    _labelled_offer(db, donation_id, org_id, FACTOR_VALUES, OfferResponse.ACCEPTED, slate_org_id=other)
    db.commit()
    with pytest.raises(ValueError, match="does not point at its candidate"):
        training.real_outcomes(db)


def test_a_sandbox_fit_records_both_counts_and_never_activates(db):
    offers = engine.run(world.generate(2, orgs=12, donations=120), 2)
    training.record_synthetic(db, "sandbox-test", 2, offers)
    report = training.train(db, include_synthetic=True)

    assert report.synthetic_available.total == len(offers)
    assert report.fitted and not report.activated
    row = report.version
    assert row.sandbox is True and row.activated is False
    assert row.synthetic_n == len(offers) and row.real_n == 0
    assert any("sandbox" in reason for reason in row.reasons)
    assert _active_weights(db) == _prior_weights()


def test_purge_removes_only_synthetic_rows_and_leaves_real_history_alone(client, db):
    org_id = uuid.UUID(h.verified_acceptor(client, db)[1])
    donor = h.donor(client)
    donation_id = uuid.UUID(h.create_donation(client, donor)["id"])
    _labelled_offer(db, donation_id, org_id, FACTOR_VALUES, OfferResponse.REJECTED)
    db.commit()
    matches_before = db.scalar(select(func.count()).select_from(Match))
    runs_before = db.scalar(select(func.count()).select_from(RankingRun))
    real_before = sorted((m.id, m.response) for m in db.scalars(select(Match)))

    offers = engine.run(world.generate(3, orgs=8, donations=40), 3)
    training.record_synthetic(db, "purge-me", 3, offers)
    training.record_synthetic(db, "keep-me", 4, offers[:5])
    removed = training.purge_synthetic(db, "purge-me")

    assert removed == len(offers)
    assert db.scalar(select(func.count()).select_from(SyntheticOutcome)) == 5
    assert db.scalar(select(func.count()).select_from(Match)) == matches_before
    assert db.scalar(select(func.count()).select_from(RankingRun)) == runs_before
    assert sorted((m.id, m.response) for m in db.scalars(select(Match))) == real_before


def test_purge_without_a_tag_removes_all_synthetic_rows(db):
    offers = engine.run(world.generate(5, orgs=8, donations=20), 5)
    training.record_synthetic(db, "a", 5, offers)
    assert training.purge_synthetic(db) == len(offers)
    assert db.scalar(select(func.count()).select_from(SyntheticOutcome)) == 0


# --- Activation is an insert ----------------------------------------------------------------


def test_activation_is_an_insert_and_the_latest_activated_row_is_the_active_model(db):
    first = _version(db, _normalised(4, 3, 2, 1, 1), activated=True)
    _version(db, _normalised(1, 1, 1, 1, 1), activated=False)
    latest = _version(db, _normalised(5, 1, 1, 1, 2), activated=True)
    assert training.active_model(db).seq == latest.seq
    assert _active_weights(db) == pytest.approx(_normalised(5, 1, 1, 1, 2))

    # A later run that does not activate writes a row and changes nothing about what is active.
    _version(db, _normalised(2, 2, 2, 2, 2), activated=False)
    assert training.active_model(db).seq == latest.seq

    # Rolling back is another insert, carrying the older weights.
    _version(db, _normalised(4, 3, 2, 1, 1), activated=True)
    assert _active_weights(db) == pytest.approx(_normalised(4, 3, 2, 1, 1))
    assert db.scalar(select(func.count()).select_from(ModelVersion)) == 5
    assert first.activated is True


def test_an_existing_version_row_cannot_be_changed_to_deactivate_it(db):
    row = _version(db, _normalised(4, 3, 2, 1, 1), activated=True)
    db.expire_all()
    row = db.get(ModelVersion, row.seq)
    row.activated = False
    with pytest.raises(AppendOnlyViolation):
        db.flush()
    db.rollback()


# --- Training on real outcomes, end to end ----------------------------------------------------


def test_a_training_run_on_real_offers_is_consistent_with_what_it_reports(client, db, monkeypatch):
    monkeypatch.setattr(learning, "MODEL_MIN_REAL_OUTCOMES", 8)
    monkeypatch.setattr(learning, "MODEL_MIN_REAL_PER_CLASS", 2)
    orgs = [uuid.UUID(h.verified_acceptor(client, db)[1]) for _ in range(3)]
    donor = h.donor(client)
    for i in range(16):
        donation_id = uuid.UUID(h.create_donation(client, donor)["id"])
        values = tuple(((i * 7 + j * 3) % 10) / 10 for j in range(5))
        response = OfferResponse.ACCEPTED if values[0] > 0.5 else OfferResponse.REJECTED
        _labelled_offer(db, donation_id, orgs[i % 3], values, response)
    db.commit()

    report = training.train(db)
    assert report.real.total == 16
    if report.activated:
        assert _active_weights(db) == pytest.approx({f: report.version.weights[f.value] for f in learning.FACTORS})
    else:
        assert _active_weights(db) == _prior_weights()
        assert report.reasons, "a run that does not activate must say why"
