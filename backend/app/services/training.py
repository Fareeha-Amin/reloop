"""Ranking-weight training: reads outcomes, fits, gates, and records one ModelVersion.

Real outcomes are the labelled Match rows (ACCEPTED, REJECTED, EXPIRED) joined to their
RankingRun's stored slate, which holds the five factor values each offer was made
against. RETRACTED offers are excluded (the donor cancelled; the acceptor did not decide)
and OPEN offers have no outcome yet.

Synthetic outcomes are read on every run and reported, but used only for a sandbox fit
(`include_synthetic`), which is recorded and never activated.

Activation is an insert. `train` decides the gate first and then inserts one ModelVersion
row carrying `activated`. Nothing is updated; the active weights are the latest activated
row, and with none the cold-start prior (SCORE_WEIGHTS) is active.

Bulk DELETE appears here only in `purge_synthetic`, the one place that removes rows, and
only from synthetic_outcomes. A test pins that allowance to this module.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import OfferResponse, ScoreFactor
from app.domain import learning
from app.domain.scoring import MatchingConfig
from app.models import Match, ModelVersion, RankingRun, SyntheticOutcome

LABELLED_RESPONSES = (OfferResponse.ACCEPTED, OfferResponse.REJECTED, OfferResponse.EXPIRED)
# The column that holds each factor's value on a synthetic row.
FACTOR_COLUMN = {
    ScoreFactor.PROXIMITY: "proximity",
    ScoreFactor.NEED_MATCH: "need_match",
    ScoreFactor.URGENCY: "urgency",
    ScoreFactor.CAPACITY_HEADROOM: "capacity_headroom",
    ScoreFactor.ACCEPTANCE_RATE: "acceptance_rate",
}


@dataclass(frozen=True)
class Counts:
    total: int
    accepted: int

    @property
    def declined(self) -> int:
        return self.total - self.accepted

    @classmethod
    def of(cls, rows: list[learning.Outcome]) -> "Counts":
        return cls(total=len(rows), accepted=sum(1 for r in rows if r.accepted))


# --- Reading outcomes -----------------------------------------------------------------------


def real_outcomes(db: Session) -> list[learning.Outcome]:
    rows = db.execute(
        select(Match, RankingRun)
        .join(RankingRun, RankingRun.id == Match.ranking_run_id)
        .where(Match.response.in_(LABELLED_RESPONSES))
    ).all()
    outcomes = []
    for match, run in rows:
        entry = next((c for c in run.slate if c["rank"] == match.rank), None)
        if entry is None or entry["organization_id"] != str(match.organization_id):
            # The offer was made to a candidate the stored slate does not show: the record
            # is inconsistent, and a fit on it would be silently wrong.
            raise ValueError(f"Match {match.id} does not point at its candidate in ranking run {run.id}.")
        values = {c["factor"]: c["value"] for c in entry["components"]}
        outcomes.append(
            learning.Outcome(
                group=str(match.donation_id),
                features=tuple(float(values[f.value]) for f in learning.FACTORS),
                accepted=match.response == OfferResponse.ACCEPTED,
            )
        )
    return outcomes


def synthetic_outcomes(db: Session) -> list[learning.Outcome]:
    rows = db.scalars(select(SyntheticOutcome).order_by(SyntheticOutcome.id)).all()
    return [
        learning.Outcome(
            group=str(row.donation_ref),
            features=tuple(float(getattr(row, FACTOR_COLUMN[f])) for f in learning.FACTORS),
            accepted=row.accepted,
        )
        for row in rows
    ]


# --- Training -----------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainReport:
    real: Counts
    synthetic_available: Counts
    include_synthetic: bool
    fitted: bool  # a fit was made (it may still not be activated)
    activated: bool
    reasons: tuple[str, ...]  # why it was not activated; empty when it was
    version: ModelVersion  # the audit row written for this attempt, always


def train(db: Session, *, include_synthetic: bool = False) -> TrainReport:
    """One training attempt. Always writes exactly one model_versions row, activated or not:

    * Below the real-outcome floor (real-only runs) nothing is fitted; the row has NULL
      weights and says why.
    * Otherwise the fit is made and gated. A fit that fails the gate is recorded with
      its reasons. A sandbox run (synthetic included) is recorded and never activated.

    Activation is decided here, before the insert, and the row is never changed."""
    real = real_outcomes(db)
    synthetic = synthetic_outcomes(db)
    real_counts = Counts.of(real)
    available = Counts.of(synthetic)
    used = synthetic if include_synthetic else []
    used_counts = Counts.of(used)

    floor = learning.floor_reason(real_counts.total, real_counts.accepted, real_counts.declined)
    evaluation: learning.Evaluation | None = None
    if floor is not None and not include_synthetic:
        activated, reasons = False, (floor,)
    else:
        evaluation = learning.evaluate(real + used)
        gate = learning.gate(
            evaluation,
            real_n=real_counts.total,
            real_accepted=real_counts.accepted,
            real_declined=real_counts.declined,
            sandbox=include_synthetic,
        )
        activated, reasons = gate.activate, gate.reasons

    fitted = evaluation is not None and evaluation.weights is not None
    row = ModelVersion(
        config_version=MatchingConfig(weights=evaluation.weights).version() if fitted else None,
        weights={f.value: w for f, w in evaluation.weights.items()} if fitted else None,
        intercept=float(evaluation.intercept) if fitted else None,
        activated=activated,
        sandbox=include_synthetic,
        reasons=list(reasons),
        real_n=real_counts.total,
        real_accepted=real_counts.accepted,
        synthetic_n=used_counts.total,
        synthetic_accepted=used_counts.accepted,
        fit=_fit_json(evaluation) if evaluation is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)  # loaded before the caller's session closes; the report reads it afterwards
    return TrainReport(real_counts, available, include_synthetic, fitted, activated, tuple(reasons), row)


class DemoNotAllowed(Exception):
    """The demo path was asked to run somewhere other than the test database."""


def assert_test_database(db: Session) -> None:
    """The demo path writes an activated fit trained on simulated data. It must never reach
    the development or any real database, so it checks the connection it was given, not
    just the configuration."""
    configured = get_settings().test_database_url
    if not configured:
        raise DemoNotAllowed("TEST_DATABASE_URL is not set; the demo path runs on the test database only.")
    bound, test = db.get_bind().engine.url, make_url(configured)  # Engine and Connection both have .engine
    if (bound.host, bound.port or 5432, bound.database) != (test.host, test.port or 5432, test.database):
        raise DemoNotAllowed(
            f"Refusing: this session is connected to {bound.database!r}, not the test database "
            f"{test.database!r}. A synthetic demo fit is never activated anywhere else."
        )


def demo_fit(db: Session) -> TrainReport:
    """Fit on the synthetic outcomes ALONE and activate the result if it beats the prior on
    held-out donations. For demonstrations on the test database only.

    This is a deliberate exception to "synthetic data never activates" (see CLAUDE.md). It
    is kept separate from `train`, whose gate is unchanged. The row is written with
    `sandbox` true and `activated` true, which is how every breakdown knows to label it a
    demo fit trained on simulated data. Real outcomes are NOT fitted, so the row records
    zero real outcomes used; how many existed is kept in `fit["real_available"]`. The point
    is to show what the synthetic rules produce."""
    assert_test_database(db)
    real_counts = Counts.of(real_outcomes(db))
    synthetic = synthetic_outcomes(db)
    synthetic_counts = Counts.of(synthetic)

    evaluation = learning.evaluate(synthetic)
    gate = learning.demo_gate(evaluation)
    fitted = evaluation.weights is not None
    fit = _fit_json(evaluation)
    fit["demo"] = True
    fit["real_available"] = {"total": real_counts.total, "accepted": real_counts.accepted}
    row = ModelVersion(
        config_version=MatchingConfig(weights=evaluation.weights).version() if fitted else None,
        weights={f.value: w for f, w in evaluation.weights.items()} if fitted else None,
        intercept=float(evaluation.intercept) if fitted else None,
        activated=gate.activate,
        sandbox=True,
        reasons=list(gate.reasons),
        real_n=0,  # real outcomes used by this fit: none
        real_accepted=0,
        synthetic_n=synthetic_counts.total,
        synthetic_accepted=synthetic_counts.accepted,
        fit=fit,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TrainReport(real_counts, synthetic_counts, True, fitted, gate.activate, tuple(gate.reasons), row)


def _fit_json(evaluation: learning.Evaluation) -> dict:
    def interval(f: ScoreFactor):
        return list(evaluation.intervals[f]) if evaluation.intervals else None

    return {
        "train_n": evaluation.train_n,
        "holdout_n": evaluation.holdout_n,
        "fitted_holdout_loss": evaluation.fitted_loss,
        "prior_holdout_loss": evaluation.prior_loss,
        "fitted_holdout_auc": evaluation.fitted_auc,
        "prior_holdout_auc": evaluation.prior_auc,
        "max_shift_from_prior": evaluation.max_shift_from_prior,
        "prior_weights": {f.value: w for f, w in evaluation.prior_weights.items()},
        "unconstrained_coefficients": (
            {f.value: c for f, c in zip(learning.FACTORS, evaluation.unconstrained)}
            if evaluation.unconstrained
            else None
        ),
        "intervals": {f.value: interval(f) for f in learning.FACTORS},
        "notes": list(evaluation.notes),
    }


# --- The active model -----------------------------------------------------------------------


def active_model(db: Session) -> ModelVersion | None:
    return db.scalar(
        select(ModelVersion).where(ModelVersion.activated.is_(True)).order_by(ModelVersion.seq.desc()).limit(1)
    )


def latest_attempt(db: Session) -> ModelVersion | None:
    """The most recent training attempt, fitted or not, activated or not."""
    return db.scalar(select(ModelVersion).order_by(ModelVersion.seq.desc()).limit(1))


def active_config(db: Session) -> MatchingConfig:
    """The configuration new rankings use: the active fit's weights, or the cold-start
    prior (MatchingConfig's default, SCORE_WEIGHTS) when no fit has been activated."""
    row = active_model(db)
    if row is None:
        return MatchingConfig()
    return MatchingConfig(weights={ScoreFactor(k): float(v) for k, v in row.weights.items()})


@dataclass(frozen=True)
class ModelView:
    config_version: str
    is_prior: bool
    trained_at: datetime | None
    real: Counts
    synthetic: Counts
    max_shift_from_prior: float | None
    is_synthetic_demo: bool = False  # fitted on simulated data for a demonstration


def model_view(db: Session, config_version: str | None) -> ModelView | None:
    """What a breakdown shows about the weights that produced it: whether they are the
    prior or a fit, and what the fit was trained on. None for a version this database
    has no record of."""
    if config_version == MatchingConfig().version():
        return ModelView(config_version, True, None, Counts(0, 0), Counts(0, 0), None)
    row = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.config_version == config_version, ModelVersion.activated.is_(True))
        .order_by(ModelVersion.seq.desc())
        .limit(1)
    )
    if row is None:
        return None
    return ModelView(
        config_version=config_version,
        is_prior=False,
        trained_at=row.created_at,
        real=Counts(row.real_n, row.real_accepted),
        synthetic=Counts(row.synthetic_n, row.synthetic_accepted),
        max_shift_from_prior=row.fit.get("max_shift_from_prior"),
        is_synthetic_demo=row.sandbox,
    )


# --- Synthetic data --------------------------------------------------------------------------


def record_synthetic(db: Session, run_tag: str, seed: int, offers: Iterable[learning.SyntheticOffer]) -> int:
    rows = [
        SyntheticOutcome(
            run_tag=run_tag,
            seed=seed,
            donation_ref=offer.donation_ref,
            organization_ref=offer.organization_ref,
            **{FACTOR_COLUMN[f]: float(offer.features[i]) for i, f in enumerate(learning.FACTORS)},
            accepted=offer.accepted,
        )
        for offer in offers
    ]
    db.add_all(rows)
    db.commit()
    return len(rows)


def purge_synthetic(db: Session, run_tag: str | None = None) -> int:
    """Delete synthetic outcomes, all of them or one run's. Touches no other table."""
    statement = delete(SyntheticOutcome)
    if run_tag is not None:
        statement = statement.where(SyntheticOutcome.run_tag == run_tag)
    result = db.execute(statement)
    db.commit()
    return result.rowcount

