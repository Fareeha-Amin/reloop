"""Ranking-weight training: synthetic outcomes (kept apart from real history) and the
versions of the weights a training run produced.

Real outcomes are not stored here: they are the Match rows and the stored slate of their
RankingRun, which already hold the five factor values each offer was made against.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import AppendOnly, Base


class SyntheticOutcome(Base):
    """One simulated offer and its simulated response. Not real history, and kept out of
    every real table on purpose: no foreign keys to donations, organisations or matches,
    so no query over matches can count one of these as a real outcome.

    This is the one table app code deletes from: `purge-synthetic` removes rows by run tag
    (see app.services.training.purge_synthetic). Nothing else is ever deleted here."""

    __tablename__ = "synthetic_outcomes"
    __table_args__ = (
        Index("ix_synthetic_outcomes_run_tag", "run_tag"),
        *(
            CheckConstraint(f"{column} >= 0 AND {column} <= 1", name=f"{column}_in_unit_interval")
            for column in ("proximity", "need_match", "urgency", "capacity_headroom", "acceptance_rate")
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_tag: Mapped[str] = mapped_column(String(64))
    seed: Mapped[int] = mapped_column(Integer)
    # Simulated identities, not references: they match nothing in the real tables.
    donation_ref: Mapped[uuid.UUID] = mapped_column()
    organization_ref: Mapped[uuid.UUID] = mapped_column()
    # The five factor values the offer was made against, as the scorer computed them.
    proximity: Mapped[float] = mapped_column(Float)
    need_match: Mapped[float] = mapped_column(Float)
    urgency: Mapped[float] = mapped_column(Float)
    capacity_headroom: Mapped[float] = mapped_column(Float)
    acceptance_rate: Mapped[float] = mapped_column(Float)
    accepted: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ModelVersion(AppendOnly, Base):
    """One row per training attempt, fitted or not. Append-only, so activation is written
    as data, never as an update:

    * `activated` is decided before the row is inserted (see app.domain.learning.gate)
      and never changes afterwards.
    * The active weights are the most recent row with `activated` true. No row means the
      cold-start prior (SCORE_WEIGHTS) is active. An attempt is never activated.
    * Rolling back is another insert: a new row carrying the older weights, activated.

    An attempt with no fit (below the real-outcome floor, or nothing to fit) has NULL
    weights, intercept, config_version and fit, and its `reasons` say why. An attempt that
    was fitted but not activated keeps everything, and its reasons say why it was not."""

    __tablename__ = "model_versions"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_version: Mapped[str | None] = mapped_column(String(32), index=True)  # NULL: no fit
    weights: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {ScoreFactor: normalised weight}
    intercept: Mapped[float | None] = mapped_column(Float)
    activated: Mapped[bool] = mapped_column(Boolean)
    sandbox: Mapped[bool] = mapped_column(Boolean)  # trained with synthetic data included
    reasons: Mapped[list[str]] = mapped_column(JSONB)  # why no fit, or why not activated (empty when activated)
    real_n: Mapped[int] = mapped_column(Integer)
    real_accepted: Mapped[int] = mapped_column(Integer)
    synthetic_n: Mapped[int] = mapped_column(Integer)  # rows used by this fit (0 unless sandbox)
    synthetic_accepted: Mapped[int] = mapped_column(Integer)
    # Diagnostics: held-out losses and AUCs, the unconstrained comparison, the intervals,
    # the split sizes. Recorded so a later reader can see how the weights were reached.
    fit: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # NULL: no fit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
