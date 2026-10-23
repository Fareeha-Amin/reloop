"""Phase 2 core loop: ranking runs, matches, handovers, status events, address-access
events, waste collectors, recyclings.

Append-only and write-once rules are enforced in application code (app.db.AppendOnly),
not by triggers. Partial indexes and CHECKs below repeat no vocabulary values.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "ranking_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("radius_km", sa.Float(), nullable=False),
        sa.Column("declines", sa.Integer(), nullable=False),
        sa.Column("config_version", sa.String(length=32), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("slate", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filtered_out", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_ranking_runs_donation_id_donations"),
        sa.PrimaryKeyConstraint("id", name="pk_ranking_runs"),
    )
    op.create_index("ix_ranking_runs_donation_id", "ranking_runs", ["donation_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ranking_run_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("offered_by", sa.String(length=32), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response", sa.String(length=32), nullable=True),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("responder_id", sa.Uuid(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("(response IS NULL) = (responded_at IS NULL)", name="ck_matches_response_has_time"),
        sa.CheckConstraint("expires_at > offered_at", name="ck_matches_expiry_after_offer"),
        sa.CheckConstraint("rank >= 1", name="ck_matches_rank_positive"),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_matches_donation_id_donations"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], name="fk_matches_organization_id_organization_profiles"
        ),
        sa.ForeignKeyConstraint(["ranking_run_id"], ["ranking_runs.id"], name="fk_matches_ranking_run_id_ranking_runs"),
        sa.ForeignKeyConstraint(["responder_id"], ["users.id"], name="fk_matches_responder_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_matches"),
        sa.UniqueConstraint("donation_id", "organization_id", name="uq_matches_donation_organization"),
    )
    op.create_index("ix_matches_donation_id", "matches", ["donation_id"])
    op.create_index(
        "uq_matches_one_open_offer_per_donation",
        "matches",
        ["donation_id"],
        unique=True,
        postgresql_where=sa.text("response IS NULL"),
    )
    op.create_index(
        "ix_matches_open_by_organization",
        "matches",
        ["organization_id"],
        postgresql_where=sa.text("response IS NULL"),
    )

    op.create_table(
        "handovers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("arranged_by_id", sa.Uuid(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_handovers_match_id_matches"),
        sa.ForeignKeyConstraint(["arranged_by_id"], ["users.id"], name="fk_handovers_arranged_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_handovers"),
        sa.UniqueConstraint("match_id", name="uq_handovers_match_id"),
    )

    op.create_table(
        "status_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("match_id", sa.Uuid(), nullable=True),
        sa.Column("cause", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_status_events_donation_id_donations"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name="fk_status_events_actor_id_users"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], name="fk_status_events_match_id_matches"),
        sa.PrimaryKeyConstraint("id", name="pk_status_events"),
    )
    op.create_index("ix_status_events_donation_id_id", "status_events", ["donation_id", "id"])

    op.create_table(
        "address_access_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["donation_id"], ["donations.id"], name="fk_address_access_events_donation_id_donations"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_address_access_events_user_id_users"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_address_access_events_organization_id_organization_profiles",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_address_access_events"),
    )
    op.create_index("ix_address_access_events_donation_id", "address_access_events", ["donation_id"])

    op.create_table(
        "waste_collectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address_text", sa.String(length=300), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("categories_accepted", postgresql.ARRAY(sa.String(length=32)), nullable=False),
        sa.Column("rate_per_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rate_per_kg >= 0", name="ck_waste_collectors_rate_non_negative"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_waste_collectors_latitude_range"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_waste_collectors_longitude_range"),
        sa.PrimaryKeyConstraint("id", name="pk_waste_collectors"),
        sa.UniqueConstraint("name", name="uq_waste_collectors_name"),
    )

    op.create_table(
        "recyclings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("donation_id", sa.Uuid(), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("rate_per_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("assigned_by_id", sa.Uuid(), nullable=False),
        _created_at(),
        sa.Column("weight_per_item_kg", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("estimated_mass_kg", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("gross_value", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("platform_fee_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("platform_fee", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("donor_credit", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "(confirmed_at IS NULL) = (gross_value IS NULL)", name="ck_recyclings_settled_when_confirmed"
        ),
        sa.ForeignKeyConstraint(["donation_id"], ["donations.id"], name="fk_recyclings_donation_id_donations"),
        sa.ForeignKeyConstraint(
            ["collector_id"], ["waste_collectors.id"], name="fk_recyclings_collector_id_waste_collectors"
        ),
        sa.ForeignKeyConstraint(["assigned_by_id"], ["users.id"], name="fk_recyclings_assigned_by_id_users"),
        sa.ForeignKeyConstraint(["confirmed_by_id"], ["users.id"], name="fk_recyclings_confirmed_by_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_recyclings"),
    )
    op.create_index("ix_recyclings_donation_id", "recyclings", ["donation_id"])
    op.create_index(
        "uq_recyclings_one_confirmed_per_donation",
        "recyclings",
        ["donation_id"],
        unique=True,
        postgresql_where=sa.text("confirmed_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("recyclings")
    op.drop_table("waste_collectors")
    op.drop_table("address_access_events")
    op.drop_table("status_events")
    op.drop_table("handovers")
    op.drop_table("matches")
    op.drop_table("ranking_runs")
