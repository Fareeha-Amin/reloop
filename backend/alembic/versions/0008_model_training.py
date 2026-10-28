"""Ranking-weight training (Phase 5).

Two new tables:

* synthetic_outcomes: simulated offers and responses from backend/sim. No foreign keys,
  so no query over the real tables can count one of them as real. Only purge-synthetic
  deletes from it. Range CHECKs on the five factor values (numeric ranges repeat no
  vocabulary, so they are allowed in the database).
* model_versions: one append-only row per training run that reached a fit. Activation is
  recorded in the row itself (`activated`), decided before insert. Nothing updates it.

Every training attempt writes a model_versions row, fitted or not; a row with no fit has
NULL weights, intercept, config_version and fit. No backfill: no attempt has ever been
made, so the cold-start prior is the active model.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FACTOR_COLUMNS = ("proximity", "need_match", "urgency", "capacity_headroom", "acceptance_rate")


def upgrade() -> None:
    checks = [
        sa.CheckConstraint(
            f"{column} >= 0 AND {column} <= 1",
            name=f"ck_synthetic_outcomes_{column}_in_unit_interval",
        )
        for column in FACTOR_COLUMNS
    ]
    op.create_table(
        "synthetic_outcomes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_tag", sa.String(length=64), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("donation_ref", sa.Uuid(), nullable=False),
        sa.Column("organization_ref", sa.Uuid(), nullable=False),
        sa.Column("proximity", sa.Float(), nullable=False),
        sa.Column("need_match", sa.Float(), nullable=False),
        sa.Column("urgency", sa.Float(), nullable=False),
        sa.Column("capacity_headroom", sa.Float(), nullable=False),
        sa.Column("acceptance_rate", sa.Float(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *checks,
        sa.PrimaryKeyConstraint("id", name="pk_synthetic_outcomes"),
    )
    op.create_index("ix_synthetic_outcomes_run_tag", "synthetic_outcomes", ["run_tag"])

    op.create_table(
        "model_versions",
        sa.Column("seq", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("config_version", sa.String(length=32), nullable=True),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("intercept", sa.Float(), nullable=True),
        sa.Column("activated", sa.Boolean(), nullable=False),
        sa.Column("sandbox", sa.Boolean(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("real_n", sa.Integer(), nullable=False),
        sa.Column("real_accepted", sa.Integer(), nullable=False),
        sa.Column("synthetic_n", sa.Integer(), nullable=False),
        sa.Column("synthetic_accepted", sa.Integer(), nullable=False),
        sa.Column("fit", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("seq", name="pk_model_versions"),
    )
    op.create_index("ix_model_versions_config_version", "model_versions", ["config_version"])


def downgrade() -> None:
    op.drop_index("ix_model_versions_config_version", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index("ix_synthetic_outcomes_run_tag", table_name="synthetic_outcomes")
    op.drop_table("synthetic_outcomes")
